"""Packaging contract tests; synthetic PE bytes are fixtures, not a runnable build."""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import package_windows_preview as package


def synthetic_pe(machine=0x8664, characteristics=0x0002):
    """Create only enough PE structure to exercise packaging identity checks."""
    data = bytearray(1024)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3C, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HHIIIHH", data, 0x84, machine, 1, 0, 0, 0, 0xF0,
                     characteristics)
    struct.pack_into("<H", data, 0x98, 0x20B)
    return bytes(data)


class WindowsPreviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.payload = self.root / "中文 payload with spaces"
        self.payload.mkdir()
        (self.payload / "yohaku_windows.exe").write_bytes(synthetic_pe())
        (self.payload / "LICENSE").write_text("Synthetic test license\n", encoding="utf-8")
        (self.payload / "THIRD_PARTY_NOTICES.md").write_text(
            "Synthetic test notices\n", encoding="utf-8")
        (self.payload / "assets").mkdir()
        (self.payload / "assets" / "说明.txt").write_text("测试资源\n", encoding="utf-8")

    def inventory(self):
        return package.build_inventory(self.payload, "2026.11.17-preview1", "synthetic-test-fixture")

    def assert_rejected(self, manifest=None):
        output = self.root / "rejected-output"
        with self.assertRaises(package.PackageError):
            package.pack(self.payload, manifest if manifest is not None else self.inventory(), output)
        self.assertFalse(output.exists(), "Validation failure must not create output artifacts")

    def test_normal_archive_hashes_launcher_and_original_payload(self):
        manifest = self.inventory()
        before = {p.relative_to(self.payload).as_posix(): p.read_bytes()
                  for p in self.payload.rglob("*") if p.is_file()}
        archive = package.pack(self.payload, manifest, self.root / "out")
        prefix = "Yohaku-2026.11.17-preview1-windows-x64/"
        with zipfile.ZipFile(archive) as zipped:
            names = zipped.namelist()
            self.assertTrue(all(name.startswith(prefix) for name in names))
            for name, data in before.items():
                self.assertEqual(zipped.read(prefix + name), data)
            receipt = json.loads(zipped.read(prefix + "package-manifest.json"))
            for entry in receipt["files"]:
                data = zipped.read(prefix + entry["path"])
                self.assertEqual(entry["sha256"], hashlib.sha256(data).hexdigest())
                self.assertEqual(entry["size"], len(data))
            recorded = {entry["path"] for entry in receipt["files"]}
            self.assertTrue(set(before).issubset(recorded))
            self.assertIn("Launch-Yohaku.cmd", recorded)
            self.assertIn("README-FIRST.txt", recorded)
            self.assertNotIn("package-manifest.json", recorded)
            launcher = zipped.read(prefix + "Launch-Yohaku.cmd").decode("utf-8-sig")
            self.assertIn("%~dp0", launcher)
            self.assertIn("yohaku_windows.exe", launcher)
            self.assertIn("logs", launcher.lower())
            self.assertIn("DisableDelayedExpansion", launcher)
            self.assertIn('> "%~dp0logs\\last-launch.log"', launcher)
            self.assertNotIn(">>", launcher)
        sums = (archive.parent / "SHA256SUMS").read_text(encoding="utf-8")
        self.assertIn(archive.name, sums)
        self.assertIn(hashlib.sha256(archive.read_bytes()).hexdigest(), sums)
        self.assertEqual(before, {p.relative_to(self.payload).as_posix(): p.read_bytes()
                                  for p in self.payload.rglob("*") if p.is_file()})

    def test_repacking_is_byte_identical(self):
        manifest = self.inventory()
        a = package.pack(self.payload, manifest, self.root / "a")
        b = package.pack(self.payload, manifest, self.root / "b")
        self.assertEqual(a.read_bytes(), b.read_bytes())

    def test_empty_payload_directories_are_preserved(self):
        (self.payload / "worlds" / "default").mkdir(parents=True)
        manifest = self.inventory()
        self.assertIn("worlds/default", manifest["directories"])
        archive = package.pack(self.payload, manifest, self.root / "out")
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(self.root / "extracted")
        restored = self.root / "extracted" / "Yohaku-2026.11.17-preview1-windows-x64" / "worlds" / "default"
        self.assertTrue(restored.is_dir())

    def test_directory_inventory_changes_are_rejected(self):
        manifest = self.inventory()
        (self.payload / "unexpected-empty").mkdir()
        self.assert_rejected(manifest)

    def test_missing_file_rejected(self):
        manifest = self.inventory()
        (self.payload / "LICENSE").unlink()
        self.assert_rejected(manifest)

    def test_extra_file_rejected(self):
        manifest = self.inventory()
        (self.payload / "extra.txt").write_text("unexpected", encoding="utf-8")
        self.assert_rejected(manifest)

    def test_modified_content_rejected_even_with_same_size(self):
        manifest = self.inventory()
        path = self.payload / "LICENSE"
        data = path.read_bytes()
        path.write_bytes(b"X" + data[1:])
        self.assert_rejected(manifest)

    def test_wrong_size_rejected(self):
        manifest = self.inventory()
        manifest["files"][0]["size"] += 1
        self.assert_rejected(manifest)

    def test_architecture_and_executable_identity_rejected(self):
        for data in (synthetic_pe(machine=0x14C), b"\x7fELF" + bytes(1020),
                     synthetic_pe(characteristics=0x2002)):
            with self.subTest(header=data[:4]):
                (self.payload / "yohaku_windows.exe").write_bytes(data)
                with self.assertRaises(package.PackageError):
                    self.inventory()

    def test_missing_notices_rejected(self):
        (self.payload / "THIRD_PARTY_NOTICES.md").unlink()
        with self.assertRaises(package.PackageError):
            self.inventory()

    def test_case_colliding_manifest_rejected(self):
        manifest = self.inventory()
        duplicate = copy.deepcopy(next(row for row in manifest["files"] if row["path"] == "LICENSE"))
        duplicate["path"] = "license"
        manifest["files"].append(duplicate)
        self.assert_rejected(manifest)

    def test_unsafe_windows_manifest_paths_rejected(self):
        original = self.inventory()
        for path in ("../outside.txt", "/absolute.txt", "C:/drive.txt", "CON.txt",
                     "assets/NUL", "trailing.", "trailing ", "stream:secret", "a\\b.txt"):
            with self.subTest(path=path):
                manifest = copy.deepcopy(original)
                manifest["files"][0]["path"] = path
                self.assert_rejected(manifest)

    def test_unsafe_entrypoint_rejected(self):
        manifest = self.inventory()
        for path in ("../yohaku.exe", "yohaku%PATH%.exe", "yohaku&extra.exe", "app.cmd"):
            with self.subTest(path=path):
                altered = copy.deepcopy(manifest)
                altered["entrypoint"] = path
                self.assert_rejected(altered)

    def test_symlink_rejected(self):
        try:
            (self.payload / "link.txt").symlink_to(self.payload / "LICENSE")
        except (OSError, NotImplementedError):
            self.skipTest("Symbolic links are unavailable for this account")
        with self.assertRaises(package.PackageError):
            self.inventory()

    def test_existing_zip_or_checksum_is_preserved(self):
        manifest = self.inventory()
        for filename in ("Yohaku-2026.11.17-preview1-windows-x64.zip", "SHA256SUMS"):
            with self.subTest(filename=filename):
                output = self.root / ("out-" + str(len(filename)))
                output.mkdir()
                existing = output / filename
                existing.write_bytes(b"keep-existing")
                with self.assertRaises(package.PackageError):
                    package.pack(self.payload, manifest, output)
                self.assertEqual(existing.read_bytes(), b"keep-existing")
                self.assertEqual([p.name for p in output.iterdir()], [filename])

    def test_metadata_rejected(self):
        original = self.inventory()
        for key, value in (("version", "../bad"), ("source_id", ""),
                           ("architecture", "arm64"), ("format", "unknown")):
            with self.subTest(key=key):
                manifest = copy.deepcopy(original)
                manifest[key] = value
                self.assert_rejected(manifest)

    def test_cli_roundtrip(self):
        script = Path(package.__file__)
        manifest = self.root / "中文 清单.json"
        environment = dict(os.environ, PYTHONIOENCODING="ascii")
        result = subprocess.run([sys.executable, str(script), "inventory", "--payload", str(self.payload),
                                 "--version", "2026.11.17-preview1", "--source-id", "synthetic-test-fixture",
                                 "--manifest", str(manifest)], capture_output=True, text=True,
                                encoding="ascii", env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["manifest"], str(manifest))
        self.assertTrue(manifest.is_file())
        output = self.root / "中文 输出"
        result = subprocess.run([sys.executable, str(script), "pack", "--payload", str(self.payload),
                                 "--manifest", str(manifest), "--output", str(output)],
                                capture_output=True, text=True, encoding="ascii", env=environment)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(Path(json.loads(result.stdout)["archive"]).is_file())
        self.assertEqual(len(list(output.glob("*.zip"))), 1)

    @unittest.skipUnless(sys.platform == "win32", "Requires the real Windows command processor")
    def test_windows_launcher_with_system_cli_fixture(self):
        """Exercise CMD with a temporary system CLI fixture, never a Yohaku build."""
        system = Path(os.environ["SystemRoot"]) / "System32"
        shutil.copyfile(system / "whoami.exe", self.payload / "yohaku_windows.exe")
        manifest = self.inventory()
        archive = package.pack(self.payload, manifest, self.root / "launcher-output")
        extracted = self.root / "中文 空格 ! launcher"
        with zipfile.ZipFile(archive) as zipped:
            zipped.extractall(extracted)
        installed = extracted / "Yohaku-2026.11.17-preview1-windows-x64"
        launcher = installed / "Launch-Yohaku.cmd"
        log = installed / "logs" / "last-launch.log"
        unrelated = self.root / "different-working-directory"
        unrelated.mkdir()
        environment = dict(os.environ, YOHAKU_TEST_LAUNCHER=str(launcher))
        # Delayed-variable expansion does not rescan exclamation marks in its
        # value. This reaches the batch file with /v:on still inherited; its
        # own DisableDelayedExpansion must protect subsequent %~dp0 uses.
        cmd = system / "cmd.exe"
        command = f'"{cmd}" /d /v:on /s /c ""!YOHAKU_TEST_LAUNCHER!""'

        def launch():
            result = subprocess.run(command, executable=str(cmd), cwd=unrelated,
                                    env=environment, input=b"", capture_output=True,
                                    timeout=15)
            # Do not include whoami output or the resulting identity log in
            # assertion messages or test-runner output.
            self.assertEqual(result.returncode, 0, "System CLI fixture launcher failed")
            self.assertTrue(log.is_file(), "Launcher did not create its package-relative log")
            self.assertGreater(log.stat().st_size, 0)

        launch()
        marker = b"YOHAKU_PREVIOUS_LAUNCH_TEST_MARKER\n"
        with log.open("ab") as stream:
            stream.write(marker)
        launch()
        self.assertTrue(marker not in log.read_bytes(), "Launcher must replace the previous log")


if __name__ == "__main__":
    unittest.main()
