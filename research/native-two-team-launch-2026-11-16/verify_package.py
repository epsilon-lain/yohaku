"""Verify this preparation package without models, network or host mutation."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def check_file(relative, digest, size=None):
    path = (ROOT / relative).resolve()
    path.relative_to(ROOT)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Hash mismatch: " + relative)
    if size is not None and len(raw) != size:
        raise ValueError("Size mismatch: " + relative)


def verify():
    package = json.loads((ROOT / "PACKAGE.json").read_text())
    for row in package["files"]:
        check_file(row["path"], row["sha256"], row["bytes"])
    preservation = json.loads((ROOT / "PRESERVATION.json").read_text())
    for row in preservation["files"]:
        check_file(row["path"], row["sha256"], row.get("bytes"))
    index = json.loads((ROOT / "seed/INDEX.json").read_text())
    assert index["native_runtime_import_status"] == "prepared_not_imported"
    assert index["preserve_all_prior_work"] is True
    for row in index["attachments"]:
        check_file("seed/" + row["path"], row["sha256"])
    assert len(index["items"]) == 12
    spec = json.loads((ROOT / "launch-spec.json").read_text())
    assert spec["status"] == "prepared_not_launched"
    assert spec["model_policy"]["model"] == "gpt-6.1-sol"
    assert spec["model_policy"]["minimum_effort"] == "high"
    assert spec["model_policy"]["leader_effort"] == "max"
    assert spec["sealed_zero_inference_guard"] == "preserve_unconditionally"
    assert spec["native_requests_sent_by_this_prep"] == 0
    return {"valid": True, "files_checked": len(package["files"]),
            "seed_items": len(index["items"]), "status": spec["status"],
            "native_import_performed": False, "native_requests_sent": 0}


if __name__ == "__main__":
    print(json.dumps(verify(), ensure_ascii=False))
