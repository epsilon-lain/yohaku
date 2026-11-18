"""Bind the C++ rank-three search to the frozen competition fixture."""

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

from verifier import stable_core

from beam_probe import EXPECTED_INSTANCE, RANK_THREE_MOVES


MANIFEST_SHA256 = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"


def encode(letter):
    return 2 * abs(letter) - 1 + (letter < 0)


def encode_table():
    for move in RANK_THREE_MOVES:
        row = stable_core.MOVE_TABLE[move]
        kind = row["category"]
        if kind == "inversion":
            code, argument = 0, 0
        elif kind == "multiplication":
            code, argument = 1 + row["invert_other"], row["other"]
        else:
            assert kind == "conjugation"
            code, argument = 3, ord(str(encode(row["conjugator"])))
        yield f"{move} {code} {row['relator']} {argument}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--max-states-per-ball", type=int, default=2_000_000)
    parser.add_argument("--seconds", type=int, default=45)
    args = parser.parse_args()
    manifest_raw = args.manifest.read_bytes()
    assert hashlib.sha256(manifest_raw).hexdigest() == MANIFEST_SHA256
    manifest = json.loads(manifest_raw)
    challenge = next(row for row in manifest["challenges"] if row["challenge_id"] == "sac-07445")
    assert challenge["instance_hash"] == EXPECTED_INSTANCE and challenge["target_relators"] == []
    start = challenge["initial_relators"] + [[3]]
    encoded_start = "".join("".join(str(encode(letter)) for letter in word) + "0" for word in start)
    fixture = "\n".join([encoded_start, *encode_table()]) + "\n"
    output = subprocess.run(
        [str(args.binary.resolve()), str(args.max_states_per_ball), str(args.seconds)],
        check=True, input=fixture, encoding="ascii", stdout=subprocess.PIPE,
        timeout=args.seconds + 5,
    )
    result = json.loads(output.stdout)
    assert len(result["reverse_orbit_layers"]) == 6 and len(result["forward_orbit_layers"]) == 5
    path = result["rank_preserving_witness"]
    if path is not None:
        route = [14, *path, 15, 15, 15]
        verdict = stable_core.verify(challenge, route, challenge["move_spec_version"], manifest["limits"])
        assert len(route) <= 14 and verdict["ok"], verdict
    else:
        route, verdict = None, None
        assert result["forward_shell_edge_slots"] == len(RANK_THREE_MOVES) * result["forward_orbit_layers"][-1]
    result.update({
        "manifest_sha256": MANIFEST_SHA256,
        "instance_hash": EXPECTED_INSTANCE,
        "fixture_sha256": hashlib.sha256(fixture.encode("ascii")).hexdigest(),
        "max_states_per_ball": args.max_states_per_ball,
        "seconds_cap": args.seconds,
        "candidate": route,
        "official_verdict": verdict,
    })
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
