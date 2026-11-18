"""Exhaust the projected rank-preserving graphs for routes of at most 14 moves."""

import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

from verifier import stable_core


MANIFEST_SHA256 = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"
INSTANCE_HASH = "sha256:f704cfdedbc0b2205b6af5e0aaff9de3ea51826121e55252dcd72ecbf7637477"
STABLE_SOURCE_SHA256 = "234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d"
CORE_SOURCE_SHA256 = "d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5"
CANON_SOURCE_SHA256 = "36cc9e6e79c8087ffaa48c50e2643872e8a0eb4ab0e134e601526604d9abf297"


def projected_moves(rank):
    return [
        row["id"]
        for row in stable_core.MOVE_TABLE
        if row["inverse"] is not None
        and row["relator"] < rank
        and row.get("other", 0) < rank
        and abs(row.get("conjugator", 0)) <= 2
    ]


def ball(root, radius, actions, state_cap, deadline):
    layer = {root}
    seen = layer.copy()
    sizes = [1]
    calls = 0
    for depth in range(1, radius + 1):
        next_layer = set()
        for measure, state in enumerate(layer):
            if measure % 1024 == 0 and monotonic() > deadline:
                raise RuntimeError(f"Time cap in radius layer {depth}")
            for move in actions:
                child, reason = stable_core.apply_move(state, move)
                assert reason is None
                key = tuple(sorted(child))
                if key not in seen:
                    next_layer.add(key)
            calls += len(actions)
            if len(seen) + len(next_layer) > state_cap:
                raise RuntimeError(f"State cap in radius layer {depth}")
        seen.update(next_layer)
        layer = next_layer
        sizes.append(len(layer))
    return seen, sizes, calls


def search(challenge, added, state_cap, deadline):
    rank = 2 + added
    start = tuple(sorted([*map(tuple, challenge["initial_relators"]), *([()] * added)]))
    goal = (*([()] * added), (1,), (2,))
    radius = 6 - added
    moves = projected_moves(rank)
    assert len(moves) == rank * (2 * rank + 3)
    seen_from_start, forward_layers, forward_calls = ball(start, radius, moves, state_cap, deadline)
    seen_from_goal, reverse_layers, reverse_calls = ball(goal, radius, moves, state_cap, deadline)
    intersections = sum(state in seen_from_goal for state in seen_from_start)
    return {
        "additions": added,
        "deletions": rank,
        "projected_rank": rank,
        "max_preserving_moves": 2 * radius,
        "each_ball_radius": radius,
        "forward_layers": forward_layers,
        "reverse_layers": reverse_layers,
        "projected_apply_calls": forward_calls + reverse_calls,
        "intersections": intersections,
        "full_routes_excluded_through_14": intersections == 0,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--min-add", type=int, choices=range(7), default=0)
    parser.add_argument("--max-add", type=int, choices=range(7), default=6)
    parser.add_argument("--states-per-ball", type=int, default=1_500_000)
    parser.add_argument("--seconds", type=int, default=45)
    args = parser.parse_args()
    assert args.min_add <= args.max_add
    raw_manifest = args.manifest.read_bytes()
    assert hashlib.sha256(raw_manifest).hexdigest() == MANIFEST_SHA256
    assert hashlib.sha256(Path(stable_core.__file__).read_bytes()).hexdigest() == STABLE_SOURCE_SHA256
    assert hashlib.sha256(Path(stable_core.core.__file__).read_bytes()).hexdigest() == CORE_SOURCE_SHA256
    assert hashlib.sha256(Path(stable_core.__file__).with_name("canon.py").read_bytes()).hexdigest() == CANON_SOURCE_SHA256
    challenge = next(row for row in json.loads(raw_manifest)["challenges"] if row["challenge_id"] == "sac-07445")
    assert challenge["instance_hash"] == INSTANCE_HASH and challenge["target_relators"] == []
    start = monotonic()
    rows = [
        search(challenge, count, args.states_per_ball, start + args.seconds)
        for count in range(args.min_add, args.max_add + 1)
    ]
    result = {
        "manifest_sha256": MANIFEST_SHA256,
        "instance_hash": INSTANCE_HASH,
        "states_per_ball_cap": args.states_per_ball,
        "seconds_cap": args.seconds,
        "elapsed_seconds": round(monotonic() - start, 3),
        "runs": rows,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
