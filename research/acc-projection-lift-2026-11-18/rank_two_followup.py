"""Try the two follow-up cases in the original, zero-stabilization graph."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from benchmark import LOCK, apply, encode
from verifier import stable_core


def rank_two_table():
    for row in stable_core.MOVE_TABLE[:14]:
        category = row["category"]
        if category == "inversion":
            kind, argument = 0, 0
        elif category == "multiplication":
            kind, argument = 1 + row["invert_other"], row["other"] + 1
        else:
            kind, argument = 3, ord(encode(((row["conjugator"],),))[0])
        yield f"{row['id']} {kind} {row['relator'] + 1} {argument}"


def run_case(binary, challenge, manifest, forward_radius, reverse_radius):
    start = tuple(map(tuple, challenge["initial_relators"]))
    target = ((1,), (2,))
    fixture = "\n".join([encode(((), *start)), encode(((), *target)), *rank_two_table()]) + "\n"
    run = subprocess.run([str(binary), "1800000", "30", str(forward_radius), str(reverse_radius)],
                         input=fixture, text=True, capture_output=True, timeout=35)
    if run.returncode:
        return {"case": challenge["challenge_id"], "instance_hash": challenge["instance_hash"],
                "status": "guard", "guard_detail": run.stderr.splitlines()}
    result = json.loads(run.stdout)
    witness = result.get("rank_preserving_witness")
    if witness is not None:
        state = start
        for move in witness:
            state = apply(state, move)
        if sorted(state) != sorted(target):
            raise RuntimeError("Rank-two witness failed official-step replay")
        moves = [*witness, 15, 15]
        verdict = stable_core.verify(challenge, moves, challenge["move_spec_version"], manifest["limits"])
        if not verdict["ok"]:
            raise RuntimeError(f"Official rejection of witness: {verdict}")
        result["certificate"] = {"moves": moves, **verdict}
    return {"case": challenge["challenge_id"], "instance_hash": challenge["instance_hash"], **result}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--forward-radius", type=int, default=6)
    parser.add_argument("--reverse-radius", type=int, default=6)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LOCK["data/manifest.json"]:
        raise RuntimeError("Frozen manifest hash mismatch")
    manifest = json.loads(raw)
    selected = {"sac-04359", "sac-08327"}
    rows = [row for row in manifest["challenges"] if row["challenge_id"] in selected]
    result = {"exactly_zero_additions": True,
              "forward_radius": args.forward_radius, "reverse_radius": args.reverse_radius,
              "runs": [run_case(args.binary.resolve(), row, manifest, args.forward_radius, args.reverse_radius)
                       for row in rows]}
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
