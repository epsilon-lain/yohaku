#!/usr/bin/env python3
"""Start a Yohaku development checkout or an installed Linux package."""
import argparse
import json
import os
from pathlib import Path
import selectors
import shutil
import signal
import subprocess
import sys
import tempfile
import time

DISPLAY_ERRORS = {
    b"Io error: Connection reset by peer (os error 104)",
    b"Io error: Broken pipe (os error 32)",
}


def supervise(command, project, output, env=None):
    child = subprocess.Popen(
        command, cwd=project, stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT, start_new_session=True, env=env,
    )
    interrupted = None
    old_handlers = {}

    def interrupt(signum, _frame):
        nonlocal interrupted
        interrupted = signum

    def terminate_group():
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=1)
        except subprocess.TimeoutExpired:
            pass
        # Native workers can outlive cargo; terminate the owned group as well.
        try:
            os.killpg(child.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        child.wait()

    selector = selectors.DefaultSelector()
    consecutive = 0
    pending = b""
    disconnected = False
    exited_at = None

    def line(data):
        nonlocal consecutive, disconnected
        output.write(data)
        output.flush()
        if data.strip() in DISPLAY_ERRORS:
            consecutive += 1
        else:
            consecutive = 0
        disconnected = consecutive >= 4

    try:
        for signum in (signal.SIGINT, signal.SIGTERM):
            old_handlers[signum] = signal.signal(signum, interrupt)
        selector.register(child.stdout, selectors.EVENT_READ)
        while not disconnected and interrupted is None:
            events = selector.select(timeout=0.1)
            if child.poll() is not None:
                if exited_at is None:
                    exited_at = time.monotonic()
                if not events and time.monotonic() - exited_at > 1:
                    break
            if not events:
                continue
            data = os.read(child.stdout.fileno(), 8192)
            if not data:
                break
            pending += data
            while b"\n" in pending and not disconnected:
                current, pending = pending.split(b"\n", 1)
                line(current + b"\n")
            # Even output without newlines must not consume unbounded memory.
            if len(pending) > 65536 and not disconnected:
                line(pending)
                pending = b""
        if pending and not disconnected and interrupted is None:
            line(pending)
        if disconnected:
            output.write(
                b"\nYohaku: repeated display disconnect; stopping this launch.\n"
                b"This does not identify the cause or repair WSLg.\n"
                b"Next diagnostic (in WSL): tail -n 60 /mnt/wslg/weston.log\n"
            )
            output.flush()
            return 70
        if interrupted is not None:
            return 128 + interrupted
        code = child.poll()
        return code if code is not None and code >= 0 else (128 - code if code is not None else 1)
    finally:
        terminate_group()
        selector.close()
        child.stdout.close()
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)


def launch_environment(backend, *, configure_x11_ime=True):
    env = os.environ.copy()
    if backend == "auto":
        try: wsl = "microsoft" in Path("/proc/version").read_text().lower()
        except OSError: wsl = False
        backend = "x11" if wsl else "native"
    if backend == "x11":
        if not env.get("DISPLAY"):
            raise ValueError("X11 display is not available (DISPLAY is unset).")

        # Forward the Fcitx5 input-method environment to X11 applications.
        if configure_x11_ime:
            env["XMODIFIERS"] = "@im=fcitx"
            env["GTK_IM_MODULE"] = "fcitx"
            env["QT_IM_MODULE"] = "fcitx"

        env.pop("WAYLAND_DISPLAY", None)
        env.pop("WAYLAND_SOCKET", None)
    return env, backend


def xdg_home(env, variable, fallback):
    path = Path(env.get(variable, ""))
    return path if path.is_absolute() else Path.home() / fallback


def seed_config(template, destination):
    if destination.exists():
        return
    data = template.read_bytes()
    json.loads(data)
    # Publish a complete file and keep an existing config if another launch wins.
    with tempfile.NamedTemporaryFile(dir=destination.parent) as temporary:
        temporary.write(data)
        temporary.flush()
        try:
            os.link(temporary.name, destination)
        except FileExistsError:
            pass


def installed_environment(project, env):
    data_dir = xdg_home(env, "XDG_DATA_HOME", ".local/share") / "yohaku"
    config_dir = xdg_home(env, "XDG_CONFIG_HOME", ".config") / "yohaku"
    world = Path(env.get("YOHAKU_WORKSPACE") or data_dir / "worlds/default").expanduser().resolve()
    loom = Path(env.get("YOHAKU_LOOM") or project / "bin/loom-linux-x86_64").expanduser().resolve()
    config_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    for name in ("ai", "shell"):
        seed_config(project / f"config/{name}.example.json", config_dir / f"{name}.json")
    from yohaku_session_startup import seed
    seed(project, world, loom)
    return dict(env, YOHAKU_CONFIG_DIR=str(config_dir), YOHAKU_WORKSPACE=str(world),
                YOHAKU_LOOM=str(loom))


def main():
    parser = argparse.ArgumentParser(description="Launch Yohaku with display-disconnect handling")
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--backend", choices=["auto", "native", "x11"], default=os.environ.get("YOHAKU_DISPLAY_BACKEND", "auto"))
    parser.add_argument("--installed", action="store_true", help="Start a prebuilt Linux package")
    args = parser.parse_args()
    if sys.platform != "linux": parser.error("Run inside WSL/Linux.")
    project = args.project.expanduser().resolve()
    try:
        if args.installed:
            command = [str(project / "bin/yohaku_compositor")]
            if not os.access(command[0], os.X_OK):
                raise ValueError(f"Installed compositor is missing or not executable: {command[0]}")
        else:
            if not (project / "Cargo.toml").is_file():
                parser.error(f"Yohaku project not found: {project}")
            command = ["cargo", "run", "--locked", "--example", "yohaku_compositor"]
            from yohaku_codex_text_service import ensure_configured
            text_service=ensure_configured(project)
            from yohaku_host_update import ensure_configured as ensure_host_update
            host_update=ensure_host_update(project)
            print('Yohaku host update: '+str(host_update),flush=True)
            print('Yohaku text service: '+str(text_service),flush=True)
        configure_x11_ime = not args.installed or shutil.which("fcitx5") is not None
        env, backend = launch_environment(args.backend, configure_x11_ime=configure_x11_ime)
        if args.installed:
            env = installed_environment(project, env)
        if backend == "x11" and configure_x11_ime:
            from yohaku_ime import ensure_x11_ime
            print("Yohaku IME: " + ensure_x11_ime(env), flush=True)
        print(f"Yohaku host display: {backend}", flush=True)
        return supervise(command, project, sys.stdout.buffer, env)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        print(f"Could not launch Yohaku: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
