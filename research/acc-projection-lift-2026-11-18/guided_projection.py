"""Look for liftable routes beyond the fixed-depth projection benchmark."""

import argparse
import hashlib
import heapq
import json
from pathlib import Path
from time import monotonic

from benchmark import LOCK, PRESERVING, apply, lift, projection, verify


ACTIONS = [
    row["id"] for row in PRESERVING if abs(row.get("conjugator", 0)) <= 2
]
GOAL = ((), (1,), (2,))


def reverse_ball(radius):
    parents = {GOAL: None}
    layer = [GOAL]
    calls = 0
    for _ in range(radius):
        next_layer = []
        for state in layer:
            for move in ACTIONS:
                child = tuple(sorted(apply(state, move)))
                calls += 1
                if child not in parents:
                    parents[child] = state
                    next_layer.append(child)
        layer = next_layer
    return parents, calls


def cyclic_length(word):
    left, right = 0, len(word)
    while right - left > 1 and word[left] == -word[right - 1]:
        left += 1
        right -= 1
    return right - left


def priority(state):
    total = sum(map(len, state))
    cyclic = sum(map(cyclic_length, state))
    return cyclic + total, total, min(map(len, state)), state


def forward_beam(initial, reverse, width, depth_cap, deadline):
    frontier = {initial: ()}
    expanded = {initial}
    calls = 0
    sizes = []
    for depth in range(1, depth_cap + 1):
        candidates = {}
        for index, (state, path) in enumerate(frontier.items()):
            if index % 256 == 0 and monotonic() > deadline:
                return None, calls, sizes, "time_cap"
            for move in ACTIONS:
                child = tuple(sorted(apply(state, move)))
                calls += 1
                if child in reverse:
                    chain = [*path, child]
                    while reverse[child] is not None:
                        child = reverse[child]
                        chain.append(child)
                    return chain, calls, sizes, f"hit_forward_depth_{depth}"
                if child not in expanded and child not in candidates:
                    candidates[child] = (*path, child)
        best = heapq.nsmallest(width, candidates, key=priority)
        sizes.append({"generated_distinct": len(candidates), "retained": len(best)})
        frontier = {state: candidates[state] for state in best}
        expanded.update(best)
    return None, calls, sizes, "depth_cap"


def label_path(ordered_start, chain):
    state = ordered_start
    ids = []
    for desired in chain:
        for move in ACTIONS:
            child = apply(state, move)
            if tuple(sorted(child)) == desired:
                ids.append(move)
                state = child
                break
        else:
            raise RuntimeError("Could not label a projected multiset edge")
    return ids


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=4096)
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    if hashlib.sha256(raw).hexdigest() != LOCK["data/manifest.json"]:
        raise RuntimeError("Frozen manifest hash mismatch")
    manifest = json.loads(raw)
    source_ids = {"sac-04359", "sac-08327"}
    began = monotonic()
    reverse, reverse_calls = reverse_ball(5)
    result = {"reverse_exact_radius": 5, "reverse_states": len(reverse),
              "reverse_apply_calls": reverse_calls, "reverse_seconds": monotonic() - began,
              "beam_width": args.width, "forward_depth_cap": 14, "runs": []}
    for challenge in manifest["challenges"]:
        if challenge["challenge_id"] not in source_ids:
            continue
        full_start = tuple(map(tuple, challenge["initial_relators"])) + ((3,),)
        reduced = projection(full_start)
        began = monotonic()
        chain, calls, sizes, stop = forward_beam(tuple(sorted(reduced)), reverse,
                                                 args.width, 14, began + 24)
        row = {"case": challenge["challenge_id"], "forward_apply_calls": calls,
               "beam_layers": sizes, "stop": stop, "search_seconds": monotonic() - began}
        if chain is not None:
            path = label_path(reduced, chain)
            row["projected_preserving_moves"] = path
            row["lift"] = lift(full_start, path)
            moves = row["lift"].get("full_preserving_witness")
            if moves is not None:
                row["lift"]["certificate"] = verify(challenge, moves, manifest["limits"])
        result["runs"].append(row)
        args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
