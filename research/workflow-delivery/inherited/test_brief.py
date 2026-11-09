"""Executable regression checks; real evidence plus labelled synthetic fixtures."""
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
sys.dont_write_bytecode = True
import brief as b

OUT = Path(os.environ.get("BRIEF_TEST_OUTPUT", "/output"))
HANDOFF = Path(__file__).resolve().parent
ROOT = HANDOFF.parent


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.docs, cls.links = b.load_dataset()
        cls.before = {p.name: digest(p.read_bytes()) for p in (ROOT / "baseline").iterdir() if p.is_file()}

    def run_cli(self, args, handoff=HANDOFF):
        return subprocess.run([sys.executable, "-B", str(handoff / "brief.py")] + args,
                              cwd=OUT, capture_output=True)

    def generate(self, directory, query="README", field="all", limit=3, handoff=HANDOFF):
        e, m = Path(directory) / "evidence.json", Path(directory) / "brief.md"
        args = ["--query", query, "--field", field, "--evidence", str(e), "--brief", str(m)]
        if limit is not None:
            args += ["--limit", str(limit)]
        p = self.run_cli(args, handoff)
        self.assertEqual(p.returncode, 0, p.stderr.decode())
        self.assertTrue(json.loads(p.stdout)["ok"])
        return e, m

    def check_oracle(self, value, docs, links, field, query, limit):
        selected = b.core.FIELDS if field == "all" else (field,)
        expected = []
        for d in sorted(docs, key=lambda x: x["source"]):
            mapping = dict(path=d["source"], title=d["title"], body=d["body"])
            matches = [f for f in selected if query.casefold() in mapping[f].casefold()]
            if matches:
                expected.append((d, matches))
        self.assertEqual(value["total"], len(expected))
        shown = expected if limit is None else expected[:limit]
        self.assertEqual(len(value["results"]), len(shown))
        for row, (doc, matched) in zip(value["results"], shown):
            self.assertEqual(row["source"], doc["source"])
            self.assertEqual(row["source_version"], doc["source_version"])
            self.assertEqual(row["matched_fields"], matched)
            self.assertEqual(row["link_counts"],
                             {s: sum(x["source"] == doc["source"] and x["status"] == s for x in links)
                              for s in b.core.STATUSES})
            lines = doc["body"].splitlines(keepends=True)
            a, z = row["line_start"], row["line_end"]
            if a == z == 0:
                self.assertEqual(row["snippet"], "")
                self.assertFalse(doc["body"].strip())
                continue
            self.assertTrue(1 <= a <= z <= len(lines))
            self.assertEqual(row["snippet"], "".join(lines[a-1:z]))
            if "body" in matched:
                hit = doc["body"].casefold().index(query.casefold())
                self.assertLessEqual(len("".join(lines[:a-1]).casefold()), hit)
                self.assertGreaterEqual(len("".join(lines[:z]).casefold()), hit + len(query.casefold()))
            else:
                first = next(i for i, line in enumerate(lines) if line.strip())
                stop = first
                while stop < len(lines) and lines[stop].strip():
                    stop += 1
                self.assertEqual((a, z), (first+1, stop))

    def test_01_real_oracle(self):
        self.assertEqual((len(self.docs), len(self.links)), (24, 77))
        self.assertEqual({s: sum(x["status"] == s for x in self.links) for s in b.core.STATUSES},
                         dict(exists=54, missing=0, unknown=23))
        for field in b.core.FIELDS + ("all",):
            for query in ("README", "项目", "AI", ".tex", "[", "not_present_381209"):
                for limit in (None, 1, 3):
                    value = b.core.search(self.docs, self.links, field, query, limit)
                    self.check_oracle(value, self.docs, self.links, field, query, limit)
                    self.assertTrue(b.verify_evidence(value, self.docs, self.links))
        for doc in self.docs:
            value = b.core.search(self.docs, self.links, "path", doc["source"])
            self.check_oracle(value, self.docs, self.links, "path", doc["source"], None)

    def test_02_cli_real_roundtrip(self):
        for query in ("README", "项目", "not_present_381209", "AI"):
            with tempfile.TemporaryDirectory(dir=OUT) as directory:
                e, m = self.generate(directory, query)
                value = json.loads(e.read_bytes())
                self.check_oracle(value, self.docs, self.links, "all", query, 3)
                self.assertEqual(m.read_bytes(), b.render_brief(value).encode("utf-8"))
                p = subprocess.run([sys.executable, "-B", str(HANDOFF / "verify.py"),
                                    "--evidence", str(e), "--brief", str(m)], capture_output=True)
                self.assertEqual(p.returncode, 0, p.stderr.decode())
                before = (e.read_bytes(), m.read_bytes())
                self.generate(directory, query)
                self.assertEqual(before, (e.read_bytes(), m.read_bytes()))

    def test_03_synthetic_exact_eol_and_fences(self):
        doc = dict(source="synthetic.tex", source_version="a"*64, title="hit",
                   body="\r\n \r\nStraße\r\n" + chr(96)*8 + "\r\nTAIL")
        for query in ("strasse", "sse\r\n" + chr(96)*3, "TAIL"):
            value = b.core.search([doc], [], "body", query)
            self.check_oracle(value, [doc], [], "body", query, None)
            rendered = b.render_brief(value).encode()
            self.assertIn(value["results"][0]["snippet"].encode(), rendered)
        value = b.core.search([doc], [], "title", "hit")
        self.assertEqual(value["results"][0]["snippet"], doc["body"][5:])
        block = b.fence(chr(96)*8 + "\r\nTAIL", "text")
        self.assertTrue(block.startswith(chr(96)*9 + "text\n"))
        self.assertIn(chr(96)*8 + "\r\nTAIL\n", block)
        links = [dict(source="synthetic.tex", status=x) for x in ("missing", "missing", "unknown")]
        value = b.core.search([doc], links, "title", "hit")
        self.assertEqual(value["results"][0]["link_counts"], dict(exists=0, missing=2, unknown=1))

    def test_04_evidence_tamper_rejected(self):
        original = b.core.search(self.docs, self.links, "all", "README", 3)
        for key, bad in (("source", "forged"), ("source_version", "0"*64), ("snippet", "forged"),
                         ("line_start", -1), ("line_end", 99999),
                         ("link_counts", dict(exists=True, missing=0, unknown=0))):
            value = copy.deepcopy(original)
            value["results"][0][key] = bad
            with self.subTest(key=key), self.assertRaises(ValueError):
                b.verify_evidence(value, self.docs, self.links)
        for value in (dict(original, total=9999), dict(original, results=[]),
                      dict(original, extra=1), dict(original, total=True)):
            with self.assertRaises(ValueError):
                b.verify_evidence(value, self.docs, self.links)
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            e, m = self.generate(directory)
            m.write_bytes(m.read_bytes() + b"\nFORGED")
            p = subprocess.run([sys.executable, "-B", str(HANDOFF / "verify.py"),
                                "--evidence", str(e), "--brief", str(m)], capture_output=True)
            self.assertEqual(p.returncode, 2)
            self.assertIn("error", json.loads(p.stdout))

    def test_05_invalid_and_protected_outputs(self):
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            e, m = Path(directory) / "e.json", Path(directory) / "m.md"
            common = ["--query", "README", "--evidence", str(e), "--brief", str(m)]
            cases = [[], common + ["--limit", "0"], common + ["--limit", "-1"],
                     common + ["--limit", "no"], common + ["--field", "bad"],
                     common + ["--lim", "1"], ["--query", " \n\t", "--evidence", str(e), "--brief", str(m)]]
            for args in cases:
                p = self.run_cli(args)
                self.assertEqual(p.returncode, 2, p.stdout)
                self.assertIn("error", json.loads(p.stdout))
            for target in (ROOT / "baseline/index.json", HANDOFF / "brief.py", ROOT / "retriever.py",
                           e, Path(directory) / "absent/file.json"):
                p = self.run_cli(["--query", "README", "--evidence", str(e), "--brief", str(target)])
                self.assertEqual(p.returncode, 2, p.stdout)
            alias = Path(directory) / "alias"
            alias.symlink_to(ROOT / "baseline", target_is_directory=True)
            p = self.run_cli(["--query", "README", "--evidence", str(e), "--brief", str(alias / "index.json")])
            self.assertEqual(p.returncode, 2)
            self.assertFalse(e.exists())

    def test_06_manifest_and_independent_transfer(self):
        manifest = json.loads((HANDOFF / "manifest.json").read_bytes())
        expected = {"brief.py", "retriever_core.py", "verify.py", "test_brief.py", "README.md", "EXPERIENCE.md"}
        self.assertEqual({x["path"] for x in manifest["files"]}, expected)
        self.assertEqual(len(manifest["files"]), len(expected))
        for row in manifest["files"]:
            self.assertIn(row["role"], ("tool", "instructions", "experience"))
            self.assertEqual(digest((HANDOFF / row["path"]).read_bytes()), row["sha256"])
        self.assertEqual(digest((HANDOFF / "retriever_core.py").read_bytes()),
                         "820925f203c3cd1aa19448ad36bc8ad4eb9277c49758ee00f817efbfa72228eb")
        with tempfile.TemporaryDirectory(dir=OUT) as directory:
            root = Path(directory)
            handoff = root / "handoff"
            handoff.mkdir()
            for row in manifest["files"]:
                shutil.copyfile(HANDOFF / row["path"], handoff / row["path"])
            shutil.copytree(ROOT / "baseline", root / "baseline", copy_function=shutil.copyfile)
            self.generate(root, "项目", handoff=handoff)
            # Intentional tampering of isolated copies, never the frozen baseline.
            target = root / "baseline/snapshot.json"
            target.write_bytes(target.read_bytes() + b" ")
            p = self.run_cli(["--query", "README", "--evidence", str(root / "bad.json"),
                              "--brief", str(root / "bad.md")], handoff)
            self.assertEqual(p.returncode, 2)
            self.assertIn("error", json.loads(p.stdout))
            self.assertFalse((root / "bad.json").exists())

    def test_07_no_input_mutation(self):
        after = {p.name: digest(p.read_bytes()) for p in (ROOT / "baseline").iterdir() if p.is_file()}
        self.assertEqual(self.before, after)
        self.assertFalse((ROOT / "baseline/__pycache__").exists())


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Contract))
    report = dict(ok=result.wasSuccessful(), tool_version=b.VERSION, tests_run=result.testsRun,
                  failures=[dict(test=str(t), traceback=e) for t, e in result.failures],
                  errors=[dict(test=str(t), traceback=e) for t, e in result.errors],
                  real_documents=24, real_references=77,
                  natural_link_counts=dict(exists=54, missing=0, unknown=23),
                  synthetic="CRLF/Unicode/fences/missing and tampered isolated copies; not natural defects")
    (OUT / "brief-test-report.json").write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode())
    if result.wasSuccessful():
        e, m = OUT / "evidence.json", OUT / "brief.md"
        code = b.main(["--query", "项目", "--field", "all", "--limit", "3",
                       "--evidence", str(e), "--brief", str(m)])
        if code:
            return code
        manifest = json.loads((HANDOFF / "manifest.json").read_bytes())
        with zipfile.ZipFile(OUT / "handoff-bundle.zip", "w", zipfile.ZIP_DEFLATED) as z:
            for name in sorted([x["path"] for x in manifest["files"]] + ["manifest.json"]):
                item = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
                item.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(item, (HANDOFF / name).read_bytes())
    print(json.dumps(report, ensure_ascii=False))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    sys.exit(main())
