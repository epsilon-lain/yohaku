"""Exact meet-in-the-middle certificate: ac-08491 has AC distance eight.

Both balls are exhaustive and unpruned. This certifies one fixed AC challenge,
not Stable AC, not other paths, and not the Andrews--Curtis conjecture.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys

from pilot import COMMIT, TARGET, apply, target_ball, total_length


def digest_states(states):
    payload = json.dumps(sorted(states), separators=(",", ":")).encode("ascii")
    return hashlib.sha256(payload).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--output", type=Path,
                        default=Path(__file__).with_name("shortest_certificate.json"))
    parser.add_argument("--submission", type=Path,
                        default=Path(__file__).with_name("submission.txt"))
    args = parser.parse_args()
    root = args.official_root.resolve()
    lock = json.loads(Path(__file__).with_name("upstream-lock.json").read_text())
    assert lock["commit"] == COMMIT
    for entry in lock["files"]:
        if hashlib.sha256((root / entry["path"]).read_bytes()).hexdigest() != entry["sha256"]:
            raise SystemExit("Official source hash mismatch: " + entry["path"])
    sys.path.insert(0, str(root / "competition/tools"))
    from verifier.core import apply_move, verify
    manifest_file = root / "competition/tools/verifier/data/manifest.json"
    manifest = json.loads(manifest_file.read_text())
    challenge = next(c for c in manifest["challenges"] if c["challenge_id"] == "ac-08491")
    start = tuple(tuple(r) for r in challenge["initial_relators"])
    witnesses = []
    for line in args.submission.read_text().splitlines():
        line = line.split("#", 1)[0].strip()
        if line.startswith("ac-08491:"):
            witnesses.append(json.loads(line.split(":", 1)[1]))
    witness = min(witnesses, key=lambda p: (len(p), p))
    verdict = verify(challenge, witness, "ac-r2-v1", manifest["limits"])
    assert verdict["ok"] is True and len(witness) == 8
    reverse, reverse_metadata = target_ball(4, apply_move)
    forward = {start}
    frontier = [start]
    frontier_sizes = [1]
    evaluations = 0
    peak = total_length(start)
    for _ in range(3):
        following = []
        for state in frontier:
            for move in range(14):
                successor = apply(state, move)
                assert successor == apply_move(state, move)
                evaluations += 1
                peak = max(peak, total_length(successor))
                if successor not in forward:
                    forward.add(successor)
                    following.append(successor)
        frontier = following
        frontier_sizes.append(len(frontier))
    intersection = forward.intersection(reverse)
    assert not intersection
    certificate = {
        "official_commit": COMMIT,
        "official_manifest_sha256": hashlib.sha256(manifest_file.read_bytes()).hexdigest(),
        "challenge_id": "ac-08491", "move_spec_version": "ac-r2-v1",
        "instance_hash": challenge["instance_hash"],
        "initial_relators": challenge["initial_relators"],
        "target_relators": [list(r) for r in TARGET],
        "witness": witness, "official_witness_verification": verdict,
        "forward_ball": {"depth": 3, "frontier_sizes": frontier_sizes,
                         "states": len(forward), "primitive_evaluations": evaluations,
                         "official_crosscheck_evaluations": evaluations,
                         "peak_total_length": peak, "length_pruning": False,
                         "states_sha256": digest_states(forward)},
        "target_ball": {**reverse_metadata,
                        "official_crosscheck_evaluations": reverse_metadata["primitive_evaluations"],
                        "states_sha256": digest_states(reverse)},
        "intersection_count": len(intersection),
        "excluded_move_lengths": {"minimum": 0, "maximum": 7},
        "global_shortest_AC_length": 8,
        "proof": "All moves have inverses. A path of length <=7 would meet the complete forward radius-3 ball and target radius-4 ball. Their intersection is empty; the verified witness has length 8.",
        "scope": "One fixed AC presentation with the exact ordered target and frozen 14-move table; no optimality claim for Stable AC or other challenges.",
        "separate_from_pilot_arm_budgets": True,
    }
    args.output.write_text(json.dumps(certificate, indent=2) + "\n")
    print(json.dumps({"challenge_id": "ac-08491", "global_shortest_AC_length": 8,
                      "forward_states": len(forward), "target_states": len(reverse),
                      "intersection_count": len(intersection)}))


if __name__ == "__main__":
    main()
