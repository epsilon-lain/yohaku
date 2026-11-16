"""New external replay of the archived native paths with pinned official code.

This is not an original Yohaku run receipt and makes no platform submission.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

PIN = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
MANIFEST_SHA = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("official_checkout", type=Path)
    parser.add_argument("fixtures", type=Path, help="directory containing ac-paths.json and ac-submission.txt")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    official = args.official_checkout.resolve()
    fixtures = args.fixtures.resolve()
    source_provenance = json.loads((Path(__file__).resolve().parent / "official-source-provenance.json").read_text())
    assert source_provenance["commit"] == PIN
    verified_sources = []
    for entry in source_provenance["files"]:
        p = official / entry["path"]
        assert sha(p) == entry["sha256"], entry["path"]
        raw = p.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        assert blob == entry["expected_git_blob"], entry["path"]
        verified_sources.append({"path": entry["path"], "sha256": sha(p), "git_blob": blob})
    manifest_path = official / "competition/tools/verifier/data/manifest.json"
    assert sha(manifest_path) == MANIFEST_SHA
    manifest = json.loads(manifest_path.read_text())
    challenge = next(c for c in manifest["challenges"] if c["challenge_id"] == "ac-08491")
    assert challenge["scored"] is True
    sys.path.insert(0, str(official / "competition/tools"))
    from verifier.core import apply_move, verify
    from verifier.specs import check_move_specs
    from verifier.submission import process_submission
    assert check_move_specs(manifest["move_specs"]) == []
    paths_file = fixtures / "ac-paths.json"
    records = json.loads(paths_file.read_text())["records"]
    assert len(records) == 8
    results = []
    for row in records:
        moves = row["moves"]
        verdict = verify(challenge, moves, challenge["move_spec_version"], manifest["limits"])
        assert verdict["ok"] is True
        assert verdict["length"] == 8
        assert verdict["peak_total_relator_length"] == row["peak"] == 9
        assert verdict["work"] == row["work"]
        state = tuple(tuple(r) for r in challenge["initial_relators"])
        states = [[list(r) for r in state]]
        for move in moves:
            state = apply_move(state, move)
            states.append([list(r) for r in state])
        assert states == row["states"]
        assert [sum(map(len, s)) for s in states] == row["lengths"]
        results.append({"moves": moves, **verdict, "archived_states_and_lengths_match": True})
    submission = fixtures / "ac-submission.txt"
    verdict = process_submission(submission.read_bytes(), manifest)
    assert verdict["accepted"] and all(v["ok"] for v in verdict["results"])
    result = {
        "kind": "new_external_review_not_original_native_receipt",
        "official_repository": "SAIRcompetition/Andrews-Curtis",
        "official_commit": PIN,
        "manifest_file_sha256": MANIFEST_SHA,
        "manifest_canonical_hash": manifest["manifest_hash"],
        "challenge": challenge,
        "move_spec_hashes_match": True,
        "archive_paths_sha256": sha(paths_file),
        "all_eight_official_core_replays": results,
        "submission_sha256": sha(submission),
        "local_submission_parser_verdict": verdict,
        "verified_official_sources": verified_sources,
        "platform_upload": False,
        "scope": [
            "Pinned official local core and parser validation, not service acceptance.",
            "Scored instance membership is established in the pinned official manifest.",
            "Raw length eight is unchanged; work48 refines the previous work49 witness.",
            "No claim about current leaderboard, globally minimal work, or unpublished cases.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({"ok": True, "paths": len(results), "scored": challenge["scored"],
                      "submission": verdict, "receipt": str(args.output)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
