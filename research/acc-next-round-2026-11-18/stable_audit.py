"""Build exact Stable AC balls for sac-01635 using the previous independent interpreter."""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--audit-script", type=Path, required=True)
    args = parser.parse_args()
    official_root = args.official_root.resolve()
    script_spec = importlib.util.spec_from_file_location("stable_audit_source", args.audit_script)
    audit = importlib.util.module_from_spec(script_spec)
    script_spec.loader.exec_module(audit)
    source_digests = audit.verify_official(official_root)
    assert audit.CAP == 5
    manifest = json.loads((official_root / "competition/tools/verifier/data/manifest.json").read_bytes())
    challenge = next(row for row in manifest["challenges"] if row["challenge_id"] == "sac-01635")
    assert challenge["scored"] and challenge["target_relators"] == []
    initial = tuple(map(tuple, challenge["initial_relators"]))
    assert len(initial) == 2
    with tempfile.TemporaryDirectory(prefix="stable-audit-empty-cache-") as cache:
        sys.pycache_prefix = cache
        sys.dont_write_bytecode = True
        sys.path.insert(0, str(official_root / "competition/tools"))
        from verifier import stable_core

        reviewer = audit.Review(stable_core)
        forward, forward_counts = reviewer.ball(initial, 4, False)
        reverse, reverse_counts = reviewer.ball((), 5, True)
        crossings = forward.keys() & reverse.keys()
        old_bound = [0, 4, 12, 4, 1, 5, 3, 3, 16, 15]
        witness = min((forward[state] + reverse[state] for state in crossings),
                      key=lambda route: (len(route), route), default=old_bound)
        verdict = stable_core.verify(challenge, list(witness), stable_core.MOVE_SPEC_VERSION,
                                     manifest["limits"])
        assert verdict["ok"], verdict
    print(json.dumps({
        "challenge_id": challenge["challenge_id"],
        "instance_hash": challenge["instance_hash"],
        "initial": initial,
        "manifest_hash": manifest["manifest_hash"],
        "official_files_verified": len(source_digests),
        "audit_source_sha256": hashlib.sha256(args.audit_script.read_bytes()).hexdigest(),
        "rank_cap": audit.CAP,
        "complete_forward": forward_counts,
        "complete_reverse": reverse_counts,
        "intersection": len(crossings),
        "witness": list(witness),
        "verdict": verdict,
        "global_minimum": len(witness),
    }, indent=2))


if __name__ == "__main__":
    main()
