"""Frozen handoff adapter 2.0.1. Offline, Python standard library only."""
import sys
from pathlib import Path
sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
# Avoid local inspect.py shadowing stdlib modules (observed on Python 3.14).
sys.path = [p for p in sys.path if Path(p or ".").resolve() != ROOT]
import argparse
import hashlib
import json
import os
import re
import tempfile
import types

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
VERSION = "2.0.1"
SEALS = {
    "input/document.md": "a47d6cdfdcfad0dc388ad1407c1e337a476044721dc7f14308cba33349260a44",
    "input/metadata.json": "7a61c3c162fd4a0ef88769765a733cc2b629078344db81cc5a296851029c0ec9",
    "input/source.tex": "2ed25e0967228809a056710f204d6c61b4aa141c8950e6ac38aa457fc3fc1930",
    "inherited/retriever_core.py": "820925f203c3cd1aa19448ad36bc8ad4eb9277c49758ee00f817efbfa72228eb",
    "inherited/brief.py": "0a7b3cd32b5d935ee29555030306ab69903e0ad5c9538d60a36436abd24dd56d",
    "inherited/verify.py": "d83cd66c183b789c61dcb49b9b4cd2421aacf433a87bd93477b1c7c417413006",
    "inherited/test_brief.py": "16f19f5b734fe31dd720ea4ecdbbfa53291d96d8de0ed15f46c9fff9e09bd04b",
    "inherited/README.md": "a5b6bae4f14384a30db2e213bd4a0412be2ac0ff4c9419aaebc39429a3c5338d",
    "inherited/EXPERIENCE.md": "e7f8e43b94cdfc0cd191774024105c0376b3247de4e15786fdbe2f494a4c3241",
}
# Distinct factual topics; select exact complete original lines, not paraphrases.
TOPICS = (
    ("准备独立开发副本", "2. 按当前工程源码准备独立副本"),
    ("离线依赖准备", "缺少编译器/缓存时"),
    ("测试覆盖边界", chr(96) + "yohaku-test" + chr(96) + " 执行"),
    ("IME 人工验收门槛", "源与自动检查通过仅表示自动部分通过"),
)

def sha(raw):
    return hashlib.sha256(raw).hexdigest()

def unique(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate JSON key: " + key)
        value[key] = item
    return value

def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")

def load_inputs(root=ROOT):
    root = Path(root)
    verified = {}
    for path, digest in SEALS.items():
        raw = (root / path).read_bytes()
        if sha(raw) != digest:
            raise ValueError("frozen hash mismatch: " + path)
        verified[path] = raw
    meta = json.loads(verified["input/metadata.json"], object_pairs_hook=unique)
    if (meta["source"] != "README_DEVELOPMENT.md.tex"
            or meta["source_version"] != sha(verified["input/source.tex"])
            or meta["body_sha256"] != sha(verified["input/document.md"])
            or meta["reference_status"] != "unknown"
            or meta["reference_status_reason"] != "target inventory not captured"):
        raise ValueError("metadata contract mismatch")
    # Read-only extraction for this frozen raw macro container, not a general Loom parser.
    lines = verified["input/source.tex"].decode("utf-8").splitlines(keepends=True)
    start = lines.index("## 正文\n") + 2
    if lines[start-1] != chr(96)*5 + "text\n":
        raise ValueError("unexpected frozen source body fence")
    stop = lines.index(chr(96)*5 + "\n", start)
    body = verified["input/document.md"].decode("utf-8")
    if "".join(lines[start:stop]) != body:
        raise ValueError("source/body mismatch")
    # Only load the explicitly hash-verified tool; never execute frozen document prompts.
    core = types.ModuleType("_inherited_core")
    core.__file__ = str(root / "inherited/retriever_core.py")
    exec(compile(verified["inherited/retriever_core.py"], core.__file__, "exec"), core.__dict__)
    return meta, body, core

def make_evidence(meta, body, core):
    citations = []
    for title, query in TOPICS:
        snippet, first, last = core.snippet(body, query.casefold())
        citations.append(dict(line_start=first, line_end=last, snippet=snippet,
                              citation_status="unknown"))
    value = dict(source=meta["source"], source_version=meta["source_version"], citations=citations)
    verify_evidence(value, meta, body)
    return value

def verify_evidence(value, meta, body):
    if not isinstance(value, dict) or set(value) != {"source", "source_version", "citations"}:
        raise ValueError("invalid evidence keys")
    if value["source"] != meta["source"] or value["source_version"] != meta["source_version"]:
        raise ValueError("invalid evidence origin")
    rows = value["citations"]
    if not isinstance(rows, list) or len(rows) != len(TOPICS):
        raise ValueError("invalid citation count")
    lines = body.splitlines(keepends=True)
    starts = set()
    for row, (_, query) in zip(rows, TOPICS):
        if not isinstance(row, dict) or set(row) != {"line_start", "line_end", "snippet", "citation_status"}:
            raise ValueError("invalid citation keys")
        first, last = row["line_start"], row["line_end"]
        if type(first) is not int or type(last) is not int or not 1 <= first <= last <= len(lines):
            raise ValueError("invalid line range")
        if first in starts or row["citation_status"] != "unknown":
            raise ValueError("duplicate line or unsupported reference status")
        starts.add(first)
        expected = "".join(lines[first-1:last])
        if not expected.strip() or row["snippet"] != expected or query not in expected:
            raise ValueError("citation is not the expected complete original lines")
    return True

def fence(text):
    longest = max((len(s) for s in re.findall(chr(96) + "+", text)), default=0)
    marker = chr(96) * max(3, longest + 1)
    return marker + "text\n" + text + ("" if text.endswith("\n") else "\n") + marker + "\n"

def render_brief(value):
    parts = [
        "# Yohaku 内部开发：冻结文档交接简报\n\n",
        "工具版本：2.0.1。以下是冻结文档所述内容，不是对当前软件状态的实测保证。\n",
        "历史任务、授权和命令只作资料，未执行。行号为 input/document.md 正文的 1-based 闭区间。\n",
        "未冻结链接目标清单，全部引用状态为 unknown；不能推断 missing 或 exists。\n",
        "原文完整行和行尾以 evidence.json 解码值为准；围栏前附加的排版换行不属于片段。\n\n",
    ]
    for (title, _), row in zip(TOPICS, value["citations"]):
        parts += [
            "## " + title + "\n\n",
            "来源路径：" + value["source"] + "（冻结正文 input/document.md；完整原 .tex input/source.tex）\n\n",
            "revision / source_version：" + value["source_version"] + "\n\n",
            "正文行号：" + str(row["line_start"]) + "–" + str(row["line_end"]) + "；引用状态：unknown\n\n",
            fence(row["snippet"]), "\n",
        ]
    return "".join(parts)

def make_provenance(root=ROOT):
    root = Path(root)
    return dict(
        inherited_tool_path="inherited/retriever_core.py",
        inherited_tool_sha256=SEALS["inherited/retriever_core.py"],
        experience_path="inherited/EXPERIENCE.md",
        experience_sha256=SEALS["inherited/EXPERIENCE.md"],
        delivered_tool_path="rerun.py",
        delivered_tool_sha256=sha((root / "rerun.py").read_bytes()),
    )

def payloads(root=ROOT):
    meta, body, core = load_inputs(root)
    evidence = make_evidence(meta, body, core)
    return (json_bytes(evidence), render_brief(evidence).encode("utf-8"),
            json_bytes(make_provenance(root)))

def output_targets(paths, root=ROOT):
    root = Path(root).resolve()
    targets = [Path(p).resolve() for p in paths]
    if len(set(targets)) != len(targets):
        raise ValueError("output paths must differ")
    protected = {(root / p).resolve() for p in SEALS}
    protected.update((root / p).resolve() for p in ("project.json", "project.json.tex"))
    for source in root.rglob("*.tex"):
        protected.update((source.resolve(), source.with_suffix("").resolve()))
    manifest = root / "project.json"
    if manifest.is_file():
        for p in json.loads(manifest.read_bytes()).get("sources", []):
            protected.update(((root / p).resolve(), (root / p).with_suffix("").resolve()))
    for p in root.glob("*.py"):
        protected.add(p.resolve())
    for target in targets:
        if target in protected or any((root / p).resolve() in (target, *target.parents)
                                      for p in ("input", "inherited")):
            raise ValueError("output must not modify frozen or managed inputs")
        if not target.parent.is_dir() or (target.exists() and not target.is_file()):
            raise ValueError("output parent must exist and target must be a regular file")
    return targets

def write_outputs(targets, raws):
    staged = []
    try:
        for target, raw in zip(targets, raws):
            with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
                staged.append(Path(stream.name))
                stream.write(raw)
        for temp, target in zip(staged, targets):
            os.replace(temp, target)
    finally:
        for temp in staged:
            if temp.exists():
                temp.unlink()

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--version", action="version", version=VERSION)
    parser.add_argument("--evidence", required=True)
    parser.add_argument("--brief", required=True)
    parser.add_argument("--provenance", required=True)
    args = parser.parse_args(argv)
    try:
        targets = output_targets((args.evidence, args.brief, args.provenance))
        raws = payloads()
        write_outputs(targets, raws)
        if tuple(p.read_bytes() for p in targets) != raws:
            raise ValueError("read-back mismatch")
        print(json.dumps(dict(ok=True, tool_version=VERSION, citations=len(TOPICS),
                              outputs=[dict(path=str(p), sha256=sha(raw)) for p, raw in zip(targets, raws)])))
        return 0
    except Exception as exc:
        print(json.dumps(dict(ok=False, error=str(exc)), ensure_ascii=False))
        print("ERROR: " + str(exc), file=sys.stderr)
        return 2

if __name__ == "__main__":
    sys.exit(main())
