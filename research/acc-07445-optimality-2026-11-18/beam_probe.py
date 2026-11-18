"""Guided pilot using the fixed competition move table."""

import argparse
import hashlib
import json
import random
from itertools import permutations
from pathlib import Path
from time import monotonic

from verifier import stable_core


EXPECTED_INSTANCE = "sha256:f704cfdedbc0b2205b6af5e0aaff9de3ea51826121e55252dcd72ecbf7637477"
RANK_THREE_MOVES = tuple(
    row["id"]
    for row in stable_core.MOVE_TABLE
    if row["inverse"] is not None
    and row["relator"] < 3
    and row.get("other", 0) < 3
    and abs(row.get("conjugator", 0)) <= 3
)
TARGETS = tuple(permutations(((1,), (2,), (3,))))


def structure_score(state):
    cyclic_lengths = []
    positive_singletons = 0
    for word in state:
        left, right = 0, len(word)
        while right - left > 1 and word[left] == -word[right - 1]:
            left += 1
            right -= 1
        cyclic_lengths.append(right - left)
        if len(word) == 1 and word[0] > 0:
            positive_singletons += 1
    return sum(map(len, state)), sum(cyclic_lengths), positive_singletons


def priority(state, mode, tie):
    length, cyclic, singletons = structure_score(state)
    if mode == 0:
        return length, cyclic, -singletons, tie
    if mode == 1:
        return cyclic, length, -singletons, tie
    return length - 2 * singletons, cyclic, tie


def reverse_ball(radius):
    paths = {state: () for state in TARGETS}
    layer = tuple(paths)
    sizes = [len(layer)]
    calls = 0
    for _ in range(radius):
        following_layer = []
        for state in layer:
            for move in RANK_THREE_MOVES:
                predecessor, reason = stable_core.apply_move(state, move)
                assert reason is None
                calls += 1
                if predecessor in paths:
                    continue
                paths[predecessor] = (stable_core.INVERSE_MOVE[move],) + paths[state]
                following_layer.append(predecessor)
        layer = following_layer
        sizes.append(len(layer))
    return paths, sizes, calls


def pilot(start, reverse, radius, width, mode, deadline, max_calls):
    rng = random.Random(20261118 + mode)
    front = {start: ()}
    expanded = {start}
    calls = 0
    layer_report = []
    for depth in range(1, 11 - radius):
        candidates = {}
        for state, path in front.items():
            if calls + len(RANK_THREE_MOVES) > max_calls or monotonic() >= deadline:
                return None, {"mode": mode, "calls": calls, "layers": layer_report,
                              "stop": "cap", "incomplete_depth": depth}
            for move in RANK_THREE_MOVES:
                child, reason = stable_core.apply_move(state, move)
                assert reason is None
                calls += 1
                suffix = reverse.get(child)
                if suffix is not None:
                    return path + (move,) + suffix, {
                        "mode": mode, "calls": calls, "layers": layer_report,
                        "stop": "intersection", "hit_depth": depth,
                    }
                if child not in expanded and child not in candidates:
                    candidates[child] = path + (move,)
        selected = sorted(candidates, key=lambda state: priority(state, mode, rng.random()))[:width]
        front = {state: candidates[state] for state in selected}
        expanded.update(front)
        layer_report.append({"depth": depth, "candidates": len(candidates), "kept": len(front)})
    return None, {"mode": mode, "calls": calls, "layers": layer_report, "stop": "depth"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--width", type=int, default=3072)
    parser.add_argument("--max-calls-per-mode", type=int, default=700_000)
    parser.add_argument("--seconds", type=float, default=45)
    args = parser.parse_args()
    raw_manifest = args.manifest.read_bytes()
    manifest = json.loads(raw_manifest)
    challenge = next(row for row in manifest["challenges"] if row["challenge_id"] == "sac-07445")
    assert challenge["instance_hash"] == EXPECTED_INSTANCE and challenge["target_relators"] == []
    start = tuple(map(tuple, challenge["initial_relators"])) + ((3,),)
    began = monotonic()
    radius = 3
    reverse, sizes, reverse_calls = reverse_ball(radius)
    if start in reverse:
        path = reverse[start]
    else:
        path = None
    runs = []
    for mode in range(3):
        if path is not None:
            break
        path, report = pilot(start, reverse, radius, args.width, mode,
                             began + args.seconds, args.max_calls_per_mode)
        runs.append(report)
    cli_route = [14, *path, 15, 15, 15] if path is not None else None
    verdict = (stable_core.verify(challenge, cli_route, challenge["move_spec_version"], manifest["limits"])
               if cli_route is not None else None)
    result = {
        "instance_hash": EXPECTED_INSTANCE,
        "manifest_sha256": hashlib.sha256(raw_manifest).hexdigest(),
        "search": "stabilize first and delete at the end; within that form, beam search",
        "beam_width": args.width,
        "max_calls_per_mode": args.max_calls_per_mode,
        "seconds_cap": args.seconds,
        "reverse_exact_layers": sizes,
        "reverse_calls": reverse_calls,
        "runs": runs,
        "official_apply_calls": reverse_calls + sum(run["calls"] for run in runs),
        "candidate": cli_route,
        "official_verdict": verdict,
        "seconds_elapsed": round(monotonic() - began, 3),
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__":
    main()
