#!/usr/bin/env python3
"""Operate the Loom-managed chat request object; host_* delegates to trusted transport.

The real world keeps files/chat-runtime-20261025/requests.json.tex. Inside a
tool sandbox its .loom and .yohaku directories are read-only. For each command
this adapter copies only the chat source and generated output into a writable
/tmp world, runs the real Rust chat_* state machine there, and writes the
resulting .tex and .json back. It never invents success and never touches
.yohaku or .loom. The host can run Loom sync on the real source afterwards.

Usage: python3 chat_state.py /world/files/.../ops/<operation>.json
"""
import json
import fcntl
import multiprocessing
import signal
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

WORLD = Path("/world")
SRC = "files/chat-runtime-20261025/requests.json.tex"
OUT = "files/chat-runtime-20261025/requests.json"
WORKSPACE = Path("/world/tools/state/yohaku-development/target/debug/yohaku_workspace")
LOOM = Path("/world/files/yohaku-default/bin/loom-linux-x86_64")
MACROS = Path("/world/macros")
AGENT_DIR = Path("/world/files/yohaku-default/agent")
REGISTRY = {
    "format": "yohaku-workspace/0.1",
    "files": [{
        "name": "chat-runtime-20261025/requests.json",
        "source": SRC,
        "output": OUT,
    }],
}


def atomic(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".chat-object-", dir=str(path.parent))
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare():
    temp = Path(tempfile.mkdtemp(prefix="chat-object-", dir="/tmp"))
    for relative in (SRC, OUT):
        source = WORLD / relative
        if source.exists():
            target = temp / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    if MACROS.is_dir():
        shutil.copytree(MACROS, temp / "macros")
    (temp / ".yohaku").mkdir(parents=True, exist_ok=True)
    atomic(temp / ".yohaku/files.json", json.dumps(REGISTRY).encode("utf-8"))
    return temp


def _commit(temp):
    # The host owns .loom and .yohaku. Copy only the Loom source and its output.
    for relative in (SRC, OUT):
        source = temp / relative
        if source.exists():
            atomic(WORLD / relative, source.read_bytes())


def workspace(temp, request):
    lock_path = WORLD / "files/chat-runtime-20261025/control/object.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original = (WORLD / SRC).read_bytes()
        for relative in (SRC, OUT):
            source = WORLD / relative
            if source.exists():
                shutil.copy2(source, temp / relative)
        def invoke(command):
            completed = subprocess.run(
                [str(WORKSPACE), "--root", str(temp), "--loom", str(LOOM)],
                input=json.dumps(command, ensure_ascii=False),
                capture_output=True, text=True, timeout=120,
            )
            try:
                value = json.loads(completed.stdout)
            except ValueError:
                raise RuntimeError("workspace returned non-JSON: " + completed.stderr[-2000:])
            if completed.returncode or not value.get("ok"):
                raise RuntimeError(str(value.get("error", "workspace command failed")))
            return value

        request = dict(request)
        respect_stop = request.pop("_respect_stop", False)
        if respect_stop and request.get("status") in ("done", "error"):
            current = invoke({"command": "chat_status", "id": request["id"]})["result"]["request"]
            if current["status"] == "stopping":
                request.update(status="cancelled", reply=None, error="stop",
                               cancel_result="stop observed before terminal commit; reply child reaped")
        value = invoke(request)
        if (WORLD / SRC).read_bytes() != original:
            raise RuntimeError("chat source changed outside adapter; no overwrite; inspect outcome")
        if request["command"] not in ("chat_status", "chat_list"):
            _commit(temp)
        return value.get("result")


def stop_requested(path, request_id):
    if not path:
        return False
    target = WORLD / path
    if not target.is_file():
        return False
    try:
        value = json.loads(target.read_text("utf-8"))
    except (OSError, ValueError):
        return False
    if value.get("stop") is not True:
        return False
    wanted = value.get("id")
    return not wanted or wanted == request_id


def model_reply(op, request, temp, stop_file):
    if str(AGENT_DIR) not in sys.path:
        sys.path.insert(0, str(AGENT_DIR))
    import yohaku_agent

    config = yohaku_agent.read_config(op.get("config_path"))
    settings = WORLD / "memory/socius.json"
    if settings.is_file():
        try:
            selected = json.loads(settings.read_text("utf-8")).get("chat", {}).get("provider", {})
            if isinstance(selected, dict):
                for key in ("base_url", "model", "protocol", "credential_source"):
                    if key in selected:
                        config[key] = selected[key]
        except (OSError, ValueError):
            pass
    if isinstance(op.get("config"), dict):
        config.update(op["config"])
    snapshot = request.get("snapshot") or {}
    context = snapshot.get("context") or {}
    history = snapshot.get("history") or []

    def execute(command):
        try:
            return workspace(temp, command)
        except RuntimeError as exc:
            raise yohaku_agent.ToolError(str(exc)) from exc

    tools = yohaku_agent.Tools(
        execute,
        lambda: context,
        config.get("permissions"),
        native=False,
    )

    if op.get("mode") == "codex":
        import yohaku_codex
        config["protocol"] = "codex-local"
        config["permissions"] = {"read": True, "write": False, "run": False,
                                 "delete": False, "import": False}
        context = dict(context, root=str(temp), page="chat-object-isolated")
        tools = yohaku_agent.Tools(execute, lambda: context,
                                   config["permissions"], native=False)
        events = []
        def emit_codex(event):
            if event.get("event") in ("model_settings", "turn_settings"):
                events.append(event)
        result = yohaku_codex.run(
            {"config": config, "prompt": request.get("prompt", ""),
             "context": context, "history": history}, tools, emit_codex)
        return {"text": result.get("text"), "usage": result.get("usage"),
                "tool_calls": result.get("tool_calls"), "provenance": "independent-codex",
                "settings": events, "diagnostic_path": result.get("diagnostic_path")}, None

    provider = yohaku_agent.Provider(config)

    def emit(event):
        if stop_requested(stop_file, request["id"]):
            provider.recovery.cancel()

    result = yohaku_agent.Agent(provider, tools, emit).run(
        request.get("prompt", ""), context, history
    )
    return {"text": result.get("text"), "usage": result.get("usage"),
            "tool_calls": result.get("tool_calls")}, None


def make_reply(op, request, temp, stop_file):
    mode = op.get("mode", "manual")
    if mode == "manual":
        reply = op.get("reply", {"text": ""})
        return reply, None, "done"
    if mode == "fake":
        return {"text": "controlled reply: " + request.get("prompt", "")[:200]}, None, "done"
    if mode == "command":
        command = op.get("command")
        if not isinstance(command, list) or not command or not all(
            isinstance(item, str) for item in command
        ):
            raise RuntimeError("command mode requires a non-empty argv list")
        completed = subprocess.run(
            command, capture_output=True, text=True,
            timeout=float(op.get("timeout", 60)),
        )
        reply = {"text": completed.stdout, "stderr": completed.stderr,
                 "exit_code": completed.returncode}
        if completed.returncode:
            return reply, "command exit " + str(completed.returncode), "error"
        return reply, None, "done"
    if mode in ("model", "codex"):
        reply, error = model_reply(op, request, temp, stop_file)
        return reply, error, "error" if error else "done"
    raise RuntimeError("unknown run mode: " + str(mode))


def reply_child(connection, ready, op, request, temp, stop_file):
    os.setsid()
    ready.set()
    try:
        connection.send({"value": make_reply(op, request, temp, stop_file)})
    except BaseException as exc:
        connection.send({"error": str(exc)})
    finally:
        connection.close()


def supervised_reply(op, request, temp, stop_file):
    ctx = multiprocessing.get_context("fork")
    receive, send = ctx.Pipe(duplex=False)
    ready = ctx.Event()
    child = ctx.Process(target=reply_child,
                        args=(send, ready, op, request, temp, stop_file))
    child.start()
    send.close()
    ready.wait(5)
    started = time.monotonic()
    heartbeat = started
    reason = None
    packet = None
    try:
        while True:
            current = workspace(temp, {"command": "chat_status", "id": request["id"]})["request"]
            if current["status"] == "stopping" or stop_requested(stop_file, request["id"]):
                reason = "stop"
                break
            if op.get("timeout") and time.monotonic() - started >= float(op["timeout"]):
                reason = "timeout"
                break
            if receive.poll(0.1):
                packet = receive.recv()
                break
            if not child.is_alive():
                raise RuntimeError("reply process exited without a result")
            if time.monotonic() - heartbeat >= 30:
                workspace(temp, {"command": "chat_update", "id": request["id"],
                                  "token": request["token"],
                                  "last_status": "independent reply process running"})
                heartbeat = time.monotonic()
    finally:
        if packet is not None:
            child.join(0.5)
        if child.is_alive():
            try:
                if ready.is_set():
                    os.killpg(child.pid, signal.SIGTERM)
                else:
                    child.terminate()
            except ProcessLookupError:
                pass
        child.join(3)
        if ready.is_set():
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        if child.is_alive():
            child.kill()
        child.join(3)
        receive.close()
    evidence = {"pid": child.pid, "exit_code": child.exitcode,
                "reaped": not child.is_alive(), "mode": op.get("mode", "manual"),
                "version": "chat-supervisor-20261026-v1"}
    if child.is_alive():
        raise RuntimeError("reply process cancellation outcome unknown")
    if reason:
        return None, reason, "cancelled" if reason == "stop" else "error", evidence
    if not packet or "error" in packet:
        return None, (packet or {}).get("error", "missing reply packet"), "error", evidence
    reply, error, status = packet["value"]
    return reply, error, status, evidence


def run_request(op, temp):
    claim = workspace(temp, {
        "command": "chat_claim",
        "runner": op.get("runner", "ai"),
        "id": op.get("id"),
        "target": op.get("target", "current"),
    })
    request = claim.get("request")
    if not request:
        return {"idle": True}
    request_id = request["id"]
    token = claim["token"]
    stop_file = op.get("stop_file")
    deadline = time.monotonic() + float(op.get("delay", 0))
    stopped = False
    while time.monotonic() < deadline:
        current = workspace(temp, {"command": "chat_status", "id": request_id})["request"]
        if current["status"] == "stopping" or stop_requested(stop_file, request_id):
            stopped = True
            break
        time.sleep(0.2)
    if stopped or stop_requested(stop_file, request_id):
        current = workspace(temp, {"command": "chat_status", "id": request_id})["request"]
        if current["status"] != "stopping":
            workspace(temp, {"command": "chat_stop", "id": request_id, "by": op.get("by", "ai")})
        result = workspace(temp, {
            "command": "chat_update",
            "id": request_id,
            "token": token,
            "status": "cancelled",
            "error": "cancelled by AI stop request",
            "cancel_result": "runner observed the stop file and cancelled the task",
        })
        return {"idle": False, "id": request_id, "status": "cancelled", "result": result}
    try:
        request["token"] = token
        reply, error, status, evidence = supervised_reply(op, request, temp, stop_file)
        if status == "cancelled":
            current = workspace(temp, {"command": "chat_status", "id": request_id})["request"]
            if current["status"] != "stopping":
                workspace(temp, {"command": "chat_stop", "id": request_id,
                                 "by": op.get("by", "ai")})
        update = {
            "command": "chat_update",
            "id": request_id,
            "token": token,
            "status": status,
            "_respect_stop": True,
            "reply": reply,
            "worker": {"pid": os.getpid(), "runner": op.get("runner", "ai"),
                       "mode": op.get("mode", "manual"), "child": evidence},
        }
        if status == "cancelled":
            update["cancel_result"] = "reply process group terminated; child reaped; exit=" + str(evidence["exit_code"])
        if error:
            update["error"] = error
        result = workspace(temp, update)
        saved = result["request"]
        return {"idle": False, "id": request_id, "status": saved["status"],
                "reply": saved.get("reply"), "error": saved.get("error"), "result": result}
    except Exception as exc:
        try:
            result = workspace(temp, {
                "command": "chat_update",
                "id": request_id,
                "token": token,
                "status": "error",
                "error": str(exc),
            })
        except Exception:
            result = None
        return {"idle": False, "id": request_id, "status": "error",
                "error": str(exc), "result": result}


HOST_TASK_CLIENT = None


def execute(op, temp):
    kind = op.get("op")
    if kind in ("host_start", "host_status", "host_cancel"):
        if HOST_TASK_CLIENT is None:
            raise RuntimeError("Host task transport is not available in the offline tool sandbox; use native codex_task_start/status/cancel. No model was started.")
        return HOST_TASK_CLIENT.dispatch(op)
    if kind == "status":
        request = {"command": "chat_status"}
        if op.get("id"):
            request["id"] = op["id"]
        if op.get("status"):
            request["status"] = op["status"]
        if op.get("limit"):
            request["limit"] = op["limit"]
        return workspace(temp, request)
    if kind == "submit":
        result = workspace(temp, {
            "command": "chat_submit",
            "prompt": op.get("prompt", ""),
            "id": op.get("id"),
            "target": op.get("target", "current"),
            "kind": op.get("kind", "chat"),
            "context": op.get("context"),
            "history": op.get("history", []),
            "config": op.get("config", {}),
        })
        return result
    if kind == "claim":
        result = workspace(temp, {
            "command": "chat_claim",
            "runner": op.get("runner", "ai"),
            "id": op.get("id"),
            "target": op.get("target", "current"),
        })
        return result
    if kind == "update":
        request = {"command": "chat_update", "id": op["id"], "token": op["token"]}
        for key in ("status", "last_status", "worker", "reply", "error", "cancel_result"):
            if key in op:
                request[key] = op[key]
        result = workspace(temp, request)
        return result
    if kind == "stop":
        result = workspace(temp, {
            "command": "chat_stop", "id": op["id"], "by": op.get("by", "ai")
        })
        return result
    if kind == "reconcile":
        result = workspace(temp, {
            "command": "chat_reconcile",
            "id": op.get("id"),
            "older_than_ms": op.get("older_than_ms", 0),
        })
        return result
    if kind == "run":
        return run_request(op, temp)
    raise RuntimeError("unknown operation: " + str(kind))


def main():
    if len(sys.argv) != 2:
        print(json.dumps({"ok": False, "error": "one operation JSON path is required"}))
        return 2
    try:
        op = json.loads(Path(sys.argv[1]).read_text("utf-8"))
        if not isinstance(op, dict):
            raise ValueError("operation must be an object")
        temp = prepare()
        try:
            result = execute(op, temp)
        finally:
            shutil.rmtree(temp, ignore_errors=True)
        print(json.dumps({"ok": True, "op": op.get("op"), "result": result},
                         ensure_ascii=False), flush=True)
        return 0
    except Exception as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    sys.exit(main())
