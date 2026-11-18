#!/usr/bin/env python3
"""Check all branches with at least two additions through 15 or 16 Stable AC moves."""

import argparse
import json
from pathlib import Path
from time import monotonic

from verifier import stable_core

from replay_candidates import MANIFEST_SHA256, digest, pinned_json


OFFICIAL_SHA256 = {
    "canon.py": "36cc9e6e79c8087ffaa48c50e2643872e8a0eb4ab0e134e601526604d9abf297",
    "core.py": "d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5",
    "stable_core.py": "234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d",
}
INSTANCES = {
    "sac-04359": "sha256:b2d07ba17521f5d1bc18fa9dd3386461de56f03fd373917cdd7eadb52cc48533",
    "sac-08327": "sha256:fb7c88b08752e06a5439b72b5433e8d38016a2b357f18c3ae6f1a09e22cdddfb",
}
def projected_actions(rank):
    actions = tuple(
        action["id"]
        for action in stable_core.MOVE_TABLE
        if action["inverse"] is not None
        and action["relator"] < rank
        and action.get("other", 0) < rank
        and abs(action.get("conjugator", 0)) <= 2
    )
    if len(actions) != rank * (2 * rank + 3) or set(actions) != {
        stable_core.INVERSE_MOVE[move] for move in actions
    }:
        raise RuntimeError(f"Incomplete or non-reversible projected move table at rank {rank}")
    return actions


def ball(root, radius, actions, deadline, state_cap):
    layer = {root}
    visited = set(layer)
    sizes = [1]
    calls = 0
    for depth in range(1, radius + 1):
        following = set()
        for index, state in enumerate(layer):
            if index % 1024 == 0 and monotonic() > deadline:
                raise RuntimeError(f"Time cap during layer {depth}")
            for action in actions:
                child, reason = stable_core.apply_move(state, action)
                if reason is not None:
                    raise RuntimeError(f"Projected move {action} rejected with {reason}")
                child = tuple(sorted(child))
                if child not in visited:
                    following.add(child)
            if len(visited) + len(following) > state_cap:
                raise RuntimeError(f"State cap during layer {depth}")
        calls += len(layer) * len(actions)
        visited.update(following)
        layer = following
        sizes.append(len(layer))
    return visited, sizes, calls


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--total-limit", type=int, choices=(15, 16), default=15)
    parser.add_argument("--states-per-ball", type=int, default=1_500_000)
    parser.add_argument("--seconds", type=int, default=120)
    args = parser.parse_args()
    official_path = Path(stable_core.__file__).parent
    for name, expected in OFFICIAL_SHA256.items():
        if digest((official_path / name).read_bytes()) != expected:
            raise ValueError(f"Unexpected official source hash for {name}")
    manifest = pinned_json(args.manifest, MANIFEST_SHA256)
    challenges = {row["challenge_id"]: row for row in manifest["challenges"]
                  if row["challenge_id"] in INSTANCES}
    for identifier, instance_hash in INSTANCES.items():
        if challenges[identifier]["instance_hash"] != instance_hash or challenges[identifier]["target_relators"] != []:
            raise ValueError(f"Unexpected instance or target for {identifier}")

    began = monotonic()
    deadline = began + args.seconds
    runs = []
    largest_feasible_count = (args.total_limit - 2) // 2
    for additions in range(2, min(largest_feasible_count, stable_core.MAX_RANK - 2) + 1):
        rank = additions + 2
        preserving = args.total_limit - additions - rank
        forward_radius = preserving // 2
        reverse_radius = preserving - forward_radius
        projected_goal = ((),) * additions + ((1,), (2,))
        actions = projected_actions(rank)
        reverse, reverse_sizes, reverse_calls = ball(
            projected_goal, reverse_radius, actions, deadline, args.states_per_ball)
        cases = []
        for identifier, challenge in challenges.items():
            projected_start = tuple(sorted(list(map(tuple, challenge["initial_relators"])) + [()] * additions))
            forward, forward_sizes, forward_calls = ball(
                projected_start, forward_radius, actions, deadline, args.states_per_ball)
            intersections = sum(state in reverse for state in forward)
            cases.append(dict(challenge_id=identifier, instance_hash=challenge["instance_hash"],
                              forward_layers=forward_sizes, forward_projected_calls=forward_calls,
                              intersections=intersections, real_routes_excluded=intersections == 0))
            del forward
        runs.append(dict(additions=additions, deletions=rank, total_limit=args.total_limit,
                         preserving_move_limit=preserving, forward_radius=forward_radius,
                         reverse_radius=reverse_radius, reverse_layers=reverse_sizes,
                         reverse_projected_calls=reverse_calls, cases=cases))
        del reverse

    if largest_feasible_count == 7:
        # The padded model would require rank nine, beyond the real move table.
        # Here seven additions force nine deletions and leave zero preserving moves.
        # Rank changes never change the length of any surviving relator, so any
        # initial nonsingleton persists and rules out a route in this branch.
        cases = []
        for identifier, challenge in challenges.items():
            lengths = list(map(len, challenge["initial_relators"]))
            cases.append(dict(challenge_id=identifier, instance_hash=challenge["instance_hash"],
                              initial_relator_lengths=lengths,
                              real_routes_excluded=any(length != 1 for length in lengths)))
        runs.append(dict(additions=7, deletions=9, total_limit=args.total_limit,
                         preserving_move_limit=0, method="nonsingleton_persists", cases=cases))

    outcome = dict(official_commit="a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e",
                   manifest_sha256=MANIFEST_SHA256, official_source_sha256=OFFICIAL_SHA256,
                   states_per_ball_cap=args.states_per_ball, seconds_cap=args.seconds,
                   elapsed_seconds=monotonic() - began, total_limit=args.total_limit,
                   additional_branches_impossible_from=largest_feasible_count + 1, runs=runs)
    args.output.write_text(json.dumps(outcome, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
