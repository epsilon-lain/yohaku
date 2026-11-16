"""Integrity checks for the small POSIX workflow journal, not a security audit."""
import importlib.util
import json
import multiprocessing
from pathlib import Path
import tempfile
import unittest

import journal


def append_worker(root, count):
    journal.ROOT = Path(root)
    for i in range(count):
        journal.record("theory", "test-worker", "test", str(i))


class JournalTests(unittest.TestCase):
    def setUp(self):
        self.original = journal.ROOT
        self.directory = tempfile.TemporaryDirectory()
        journal.ROOT = Path(self.directory.name)
        (journal.ROOT / "snapshots").mkdir()

    def tearDown(self):
        journal.ROOT = self.original
        self.directory.cleanup()

    def test_snapshot_survives_source_change_and_detects_corruption(self):
        artifact = journal.ROOT / "result.txt"
        artifact.write_text("version one")
        event = journal.record("theory", "test", "math_publish", "claim", ["result.txt"])
        artifact.write_text("version two")
        self.assertEqual(journal.verify(), 1)
        snapshot = journal.ROOT / event["artifacts"][0]["snapshot"]
        snapshot.write_text("corrupted")
        with self.assertRaises(AssertionError):
            journal.verify()

    def test_chain_detects_edited_history(self):
        journal.record("application", "test", "test", "one")
        journal.record("application", "test", "test", "two")
        path = journal.ROOT / "events/application.jsonl"
        rows = path.read_text().splitlines()
        first = json.loads(rows[0])
        first["summary"] = "changed"
        rows[0] = json.dumps(first)
        path.write_text("\n".join(rows) + "\n")
        with self.assertRaises(AssertionError):
            journal.verify()

    def test_concurrent_append_sequence(self):
        children = [multiprocessing.Process(target=append_worker,
                    args=(str(journal.ROOT), 6)) for _ in range(4)]
        for child in children:
            child.start()
        for child in children:
            child.join(timeout=10)
            self.assertEqual(child.exitcode, 0)
        self.assertEqual(journal.verify(), 24)


if __name__ == "__main__":
    unittest.main()
