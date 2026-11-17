#!/usr/bin/env python3
"""Inventory and package an already-built, clean native Windows x64 payload.

This does not build Yohaku, discover runtime dependencies, or verify that a
program starts on Windows. The inventory binds the selected payload bytes.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import struct
import tempfile
import zipfile


FORMAT = "yohaku-windows-preview/1"
GENERATED = {"launch-yohaku.cmd", "readme-first.txt", "package-manifest.json"}
DEVICES = {"CON", "PRN", "AUX", "NUL"} | {
    prefix + digit for prefix in ("COM", "LPT") for digit in "123456789¹²³"
}


class PackageError(ValueError):
    """The payload or package description is not suitable for packaging."""


def safe_path(value: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise PackageError("Paths must be nonempty relative POSIX paths")
    parts = value.split("/")
    for part in parts:
        if (not part or part in (".", "..") or part.endswith((" ", "."))
                or any(ord(c) < 32 or c in '<>:"|?*' for c in part)
                or part.split(".")[0].upper() in DEVICES):
            raise PackageError(f"Unsafe Windows path: {value!r}")
    return value


def reject_link(path: Path) -> os.stat_result:
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise PackageError(f"Links and Windows reparse points are not allowed: {path}")
    return info


def scan(payload: Path, directories: list[str] | None = None) -> dict[str, Path]:
    payload = Path(payload)
    if not stat.S_ISDIR(reject_link(payload).st_mode):
        raise PackageError("Payload must be a directory")
    files: dict[str, Path] = {}
    seen: set[str] = set()
    for root, dirs, names in os.walk(payload, followlinks=False):
        for name in sorted(dirs + names):
            path = Path(root) / name
            info = reject_link(path)
            relative = safe_path(path.relative_to(payload).as_posix())
            folded = relative.casefold()
            if folded in seen:
                raise PackageError(f"Windows case-insensitive path collision: {relative}")
            seen.add(folded)
            if relative.split("/")[0].casefold() in GENERATED:
                raise PackageError(f"Payload uses a reserved generated path: {relative}")
            if stat.S_ISREG(info.st_mode):
                files[relative] = path
            elif stat.S_ISDIR(info.st_mode):
                if directories is not None:
                    directories.append(relative)
            else:
                raise PackageError(f"Payload contains a non-regular file: {relative}")
    return dict(sorted(files.items()))


def metadata(path: Path, relative: str) -> dict:
    digest = hashlib.sha256()
    size = 0
    with path.open("rb") as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
            size += len(chunk)
    return {"path": relative, "size": size, "sha256": digest.hexdigest()}


def validate_header(manifest: dict) -> None:
    if not isinstance(manifest, dict) or manifest.get("format") != FORMAT:
        raise PackageError(f"Expected manifest format {FORMAT}")
    if manifest.get("architecture") != "x64":
        raise PackageError("Only the native Windows x64 preview is supported")
    version = manifest.get("version")
    if not isinstance(version, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,95}", version):
        raise PackageError("Version must be a nonempty filename-safe identifier")
    source = manifest.get("source_id")
    if not isinstance(source, str) or not source.strip() or len(source) > 512 or any(ord(c) < 32 for c in source):
        raise PackageError("source_id must identify the maintainer's actual source snapshot")
    entry = safe_path(manifest.get("entrypoint"))
    if not re.fullmatch(r"[A-Za-z0-9_./-]+", entry) or not entry.lower().endswith(".exe"):
        raise PackageError("Entrypoint must be an ASCII relative .exe path without shell metacharacters")


def validate_pe(path: Path) -> None:
    with path.open("rb") as stream:
        header = stream.read(64)
        if len(header) != 64 or header[:2] != b"MZ":
            raise PackageError("Entrypoint is not a Windows PE executable")
        offset = struct.unpack_from("<I", header, 60)[0]
        if offset < 64 or offset > path.stat().st_size - 26:
            raise PackageError("Invalid PE header offset")
        stream.seek(offset)
        pe = stream.read(24)
        if pe[:4] != b"PE\0\0" or len(pe) != 24:
            raise PackageError("Invalid PE signature")
        machine, = struct.unpack_from("<H", pe, 4)
        optional_size, characteristics = struct.unpack_from("<HH", pe, 20)
        optional = stream.read(optional_size)
        if (machine != 0x8664 or optional_size < 2 or len(optional) != optional_size
                or struct.unpack_from("<H", optional)[0] != 0x20B):
            raise PackageError("Entrypoint must be an AMD64 PE32+ executable")
        if not characteristics & 0x2 or characteristics & 0x2000:
            raise PackageError("Entrypoint must be an executable image, not a DLL")


def build_inventory(payload: Path, version: str, source_id: str,
                    entrypoint: str = "yohaku_windows.exe") -> dict:
    manifest = {"format": FORMAT, "architecture": "x64", "version": version,
                "source_id": source_id, "entrypoint": entrypoint}
    validate_header(manifest)
    directories: list[str] = []
    files = scan(Path(payload), directories)
    if entrypoint not in files:
        raise PackageError("Entrypoint is missing from the payload")
    for required in ("LICENSE", "THIRD_PARTY_NOTICES.md"):
        if required not in files:
            raise PackageError(f"Required distribution notice is missing: {required}")
    validate_pe(files[entrypoint])
    manifest["files"] = [metadata(path, relative) for relative, path in files.items()]
    manifest["directories"] = sorted(directories)
    return manifest


def verify_payload(payload: Path, manifest: dict) -> dict[str, Path]:
    validate_header(manifest)
    expected: dict[str, dict] = {}
    items = manifest.get("files")
    if not isinstance(items, list) or not items:
        raise PackageError("Manifest must contain a nonempty file inventory")
    folded = set()
    for item in items:
        if not isinstance(item, dict):
            raise PackageError("Invalid file record")
        relative = safe_path(item.get("path"))
        if relative.casefold() in folded:
            raise PackageError(f"Duplicate inventory path: {relative}")
        folded.add(relative.casefold())
        if (type(item.get("size")) is not int or item["size"] < 0
                or not isinstance(item.get("sha256"), str)
                or not re.fullmatch("[0-9a-f]{64}", item["sha256"])):
            raise PackageError(f"Invalid size or SHA-256 for {relative}")
        expected[relative] = item
    directories: list[str] = []
    files = scan(payload, directories)
    expected_dirs = manifest.get("directories")
    if not isinstance(expected_dirs, list) or any(not isinstance(item, str) for item in expected_dirs):
        raise PackageError("Manifest must contain a directory inventory")
    for relative in expected_dirs:
        safe_path(relative)
    if (len(set(item.casefold() for item in expected_dirs)) != len(expected_dirs)
            or sorted(expected_dirs) != sorted(directories)):
        raise PackageError("Payload directory inventory mismatch")
    if set(files) != set(expected):
        missing = sorted(set(expected) - set(files))
        extra = sorted(set(files) - set(expected))
        raise PackageError(f"Payload inventory mismatch; missing={missing}, extra={extra}")
    for relative, path in files.items():
        if metadata(path, relative) != expected[relative]:
            raise PackageError(f"Payload bytes differ from inventory: {relative}")
    for required in (manifest["entrypoint"], "LICENSE", "THIRD_PARTY_NOTICES.md"):
        if required not in files:
            raise PackageError(f"Required package file is missing: {required}")
    validate_pe(files[manifest["entrypoint"]])
    return files


def json_bytes(value: dict) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def generated_files(manifest: dict) -> dict[str, bytes]:
    entry = manifest["entrypoint"].replace("/", "\\")
    launcher = f'''@echo off
setlocal EnableExtensions DisableDelayedExpansion
set "ERRORLEVEL="
cd /d "%~dp0"
if errorlevel 1 goto location_error
if not exist "logs" mkdir "logs"
if not exist "logs" goto location_error
if not exist "{entry}" goto missing_exe
"%~dp0{entry}" > "%~dp0logs\\last-launch.log" 2>&1
set "YOHAKU_EXIT=%ERRORLEVEL%"
if "%YOHAKU_EXIT%"=="0" exit /b 0
echo Yohaku exited with code %YOHAKU_EXIT%.
echo Log: "%~dp0logs\\last-launch.log"
pause
exit /b %YOHAKU_EXIT%
:missing_exe
echo Yohaku executable is missing. Extract the complete ZIP before launching.
pause
exit /b 1
:location_error
echo Cannot use this folder. Extract the ZIP to a writable local folder.
pause
exit /b 1
'''
    readme = f'''Yohaku Windows 技术预览版 {manifest['version']}

请先完整解压 ZIP，再双击 Launch-Yohaku.cmd。
请保留文件夹中的所有运行文件，并放在可以写入的本地目录。
启动器从本目录运行程序，将本次启动输出保存到 logs/last-launch.log。
再次启动会覆盖该日志；需要反馈时请先复制相关错误内容。
启动失败时请提供版本号、Windows 版本和日志中相关的错误内容。
不要直接从压缩文件内启动程序。

此包为技术预览。具体已验证功能和已知问题请查看对应 GitHub Release。
账号、模型与联网功能按实际程序的设置配置；打包工具不配置账号或模型。
此文件及打包校验不能代替真实 Windows 启动与依赖验收。
'''
    return {"Launch-Yohaku.cmd": launcher.replace("\n", "\r\n").encode("ascii"),
            "README-FIRST.txt": readme.replace("\n", "\r\n").encode("utf-8-sig")}


def zip_info(path: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(2020, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_DEFLATED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def pack(payload: Path, manifest: dict, output: Path) -> Path:
    payload, output = Path(payload), Path(output)
    if output.resolve().is_relative_to(payload.resolve()):
        raise PackageError("Output directory must be outside the payload")
    files = verify_payload(payload, manifest)
    folder = f"Yohaku-{manifest['version']}-windows-x64"
    archive_path = output / (folder + ".zip")
    sums_path = output / "SHA256SUMS"
    if archive_path.exists() or sums_path.exists():
        raise PackageError("Output already exists; select a fresh output directory")
    generated = generated_files(manifest)
    package_manifest = dict(manifest)
    package_manifest["files"] = sorted(manifest["files"] + [
        {"path": name, "size": len(content), "sha256": hashlib.sha256(content).hexdigest()}
        for name, content in generated.items()
    ], key=lambda item: item["path"])
    generated["package-manifest.json"] = json_bytes(package_manifest)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".yohaku-package-", dir=output) as temp:
        staged = Path(temp) / archive_path.name
        with zipfile.ZipFile(staged, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            expected = {item["path"]: item for item in manifest["files"]}
            for name in sorted(manifest["directories"]):
                info = zip_info(folder + "/" + name + "/")
                info.external_attr = (0o40755 << 16) | 0x10
                archive.writestr(info, b"")
            for name in sorted(set(files) | set(generated)):
                with archive.open(zip_info(folder + "/" + name), "w") as destination:
                    if name in generated:
                        destination.write(generated[name])
                    else:
                        reject_link(files[name])
                        digest = hashlib.sha256()
                        size = 0
                        with files[name].open("rb") as source:
                            while chunk := source.read(1024 * 1024):
                                destination.write(chunk)
                                digest.update(chunk)
                                size += len(chunk)
                        if size != expected[name]["size"] or digest.hexdigest() != expected[name]["sha256"]:
                            raise PackageError(f"Payload changed while packaging: {name}")
        checksum = metadata(staged, staged.name)["sha256"] + "  " + archive_path.name + "\n"
        created = []
        try:
            with archive_path.open("xb") as target, staged.open("rb") as source:
                created.append(archive_path)
                shutil.copyfileobj(source, target)
            with sums_path.open("x", encoding="ascii", newline="\n") as stream:
                created.append(sums_path)
                stream.write(checksum)
        except BaseException:
            for path in created:
                path.unlink(missing_ok=True)
            raise
    return archive_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    inventory = commands.add_parser("inventory", help="Inventory a clean, already-built payload")
    inventory.add_argument("--payload", type=Path, required=True)
    inventory.add_argument("--version", required=True)
    inventory.add_argument("--source-id", required=True)
    inventory.add_argument("--entrypoint", default="yohaku_windows.exe")
    inventory.add_argument("--manifest", type=Path, required=True)
    package = commands.add_parser("pack", help="Verify inventory and create the portable ZIP")
    package.add_argument("--payload", type=Path, required=True)
    package.add_argument("--manifest", type=Path, required=True)
    package.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "inventory":
            if args.manifest.resolve().is_relative_to(args.payload.resolve()):
                raise PackageError("Inventory manifest must be stored outside the payload")
            value = build_inventory(args.payload, args.version, args.source_id, args.entrypoint)
            args.manifest.parent.mkdir(parents=True, exist_ok=True)
            with args.manifest.open("xb") as stream:
                stream.write(json_bytes(value))
            print(json.dumps({"manifest": str(args.manifest)}, ensure_ascii=True))
        else:
            value = json.loads(args.manifest.read_text(encoding="utf-8-sig"))
            print(json.dumps({"archive": str(pack(args.payload, value, args.output))}, ensure_ascii=True))
        return 0
    except (PackageError, OSError, json.JSONDecodeError) as exc:
        parser.exit(1, f"Packaging failed: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
