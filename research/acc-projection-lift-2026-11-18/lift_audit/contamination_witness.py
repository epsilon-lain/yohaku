#!/usr/bin/env python3
"""Produce independently replayable projection-fibre witnesses using pinned moves."""

import argparse
import hashlib
import json
from pathlib import Path
from random import Random
from time import monotonic

from verifier import core, stable_core

from audit_lift import (FULL_MOVES, FULL_TARGET, MANIFEST_SHA, PROJECTED_MOVES,
                        PROJECTED_TARGET, canonical, lift_fibres, move,
                        path_trace, project, verify)


FRESH = ("04359", "08327", "09594", "04416", "07667", "00066", "00626", "09241", "04551")
RANK_TWO = range(core.NUM_MOVES)
TARGET_TWO = ((1,), (2,))


def move_id(category, relator, **operands):
    return next(row["id"] for row in stable_core.MOVE_TABLE
                if row["category"] == category and row["relator"] == relator
                and all(row[key] == value for key, value in operands.items()))


def reverse_rank_two(radius):
    paths = {TARGET_TWO: (), TARGET_TWO[::-1]: ()}
    layer = list(paths)
    for _ in range(radius):
        upcoming = []
        for state in layer:
            for action in RANK_TWO:
                child = core.apply_move(state, action)
                if child not in paths:
                    paths[child] = (core.INVERSE_MOVE[action], *paths[state])
                    upcoming.append(child)
        layer = upcoming
    return paths


def cyclic_length(word):
    left = 0
    right = len(word) - 1
    while left < right and word[left] == -word[right]:
        left += 1
        right -= 1
    return right + 1 - left


def rank_score(state, cyclic_weight):
    lengths = tuple(map(len, state))
    cyclic = sum(map(cyclic_length, state))
    return sum(lengths) + cyclic_weight * cyclic, max(lengths)


def guided_route(start, reverse, width, depth, seed):
    front = {start: ()}
    seen = {start}
    jitter = Random(seed)
    for _ in range(depth + 1):
        matches = [route + reverse[state] for state, route in front.items() if state in reverse]
        if matches:
            return min(matches, key=lambda route: (len(route), route))
        upcoming = {}
        for state, prefix in front.items():
            for action in RANK_TWO:
                child = core.apply_move(state, action)
                if child not in seen:
                    upcoming.setdefault(child, prefix + (action,))
        ordered = sorted(upcoming, key=lambda state: (*rank_score(state, seed % 3), jitter.random()))
        selected = ordered[:width]
        front = {state: upcoming[state] for state in selected}
        seen.update(front)
    return None


def best_invisible_repair(start, depth):
    fixed_shadow = project(start)
    if canonical(start) == FULL_TARGET:
        return ()
    routes = {start: ()}
    layer = [start]
    for _ in range(depth):
        upcoming = []
        for state in layer:
            for action in FULL_MOVES:
                child = move(state, action)
                if child not in routes and project(child) == fixed_shadow:
                    routes[child] = (*routes[state], action)
                    if canonical(child) == FULL_TARGET:
                        return routes[child]
                    upcoming.append(child)
        layer = upcoming
    return None


def inspect_geodesic_suffix(challenge, source, route, contamination, limits):
    goal = path_trace(source, route)[-1]
    prefix = (14, *route[:-1], contamination)
    dirty = path_trace(source, (*route[:-1], contamination))[-1]
    assert path_trace(tuple(map(tuple, challenge["initial_relators"])), prefix)[-1] == dirty
    dirty_shadow = project(dirty)
    goal_shadow = project(goal)
    assert canonical(goal_shadow) == PROJECTED_TARGET
    assert canonical(dirty_shadow) != PROJECTED_TARGET
    last_action = route[-1]
    assert move(dirty_shadow, last_action) == goal_shadow
    bad_endpoint = move(dirty, last_action)
    assert project(bad_endpoint) == goal_shadow
    for ordered in (True, False):
        fibre = lift_fibres(dirty, [dirty_shadow, goal_shadow], ordered=ordered)
        assert fibre["layer_sizes"] == [1, 1] and fibre["successful_lift"] is None
        assert fibre["final_fibre"] == [bad_endpoint]
    dirty_attempt = (*prefix, last_action, 15, 15, 15)
    rejection = verify(dirty_attempt, challenge, limits)
    assert rejection["code"] == "E_MOVE_NOT_APPLICABLE"
    inverse = stable_core.INVERSE_MOVE[contamination]
    assert project(move(dirty, inverse)) == dirty_shadow
    assert canonical(path_trace(dirty, [inverse, last_action])[-1]) == FULL_TARGET
    before_route = (*prefix, inverse, last_action, 15, 15, 15)
    before = verify(before_route, challenge, limits)
    assert before["ok"]
    after_repair = best_invisible_repair(bad_endpoint, 5)
    assert after_repair is not None and len(after_repair) == 5
    after_route = (*prefix, last_action, *after_repair, 15, 15, 15)
    after = verify(after_route, challenge, limits)
    assert after["ok"]
    return {
        "reachable_prefix": prefix,
        "full_start": dirty,
        "projected_start": dirty_shadow,
        "projected_goal": goal_shadow,
        "exact_projected_distance": 1,
        "exact_full_rank_three_distance": 2,
        "projected_move_id": last_action,
        "one_step_lifts_ordered_and_unordered": fibre,
        "rejected": {"moves": dirty_attempt, "verdict": rejection},
        "repair_before_projected_edge": {
            "invisible_moves": [inverse], "moves": before_route, "verdict": before,
        },
        "shortest_repair_after_edge_holding_ordered_projection": {
            "invisible_moves": after_repair, "moves": after_route, "verdict": after,
        },
    }


def inspect(challenge, source, route, limits):
    expected = canonical(path_trace(source, route)[-1])
    assert expected == FULL_TARGET
    shell = (14, *route)
    good_attempt = (*shell, 15, 15, 15)
    contaminated_step = move_id("conjugation", 0, conjugator=3)
    bad_attempt = (*shell, contaminated_step, 15, 15, 15)
    clean_endpoint, contaminated_endpoint = path_trace(source, (*route, contaminated_step))[-2:]
    assert clean_endpoint != contaminated_endpoint and project(clean_endpoint) == project(contaminated_endpoint)
    good = verify(good_attempt, challenge, limits)
    bad = verify(bad_attempt, challenge, limits)
    repair = best_invisible_repair(contaminated_endpoint, 1)
    assert repair is not None and len(repair) == 1
    repaired_attempt = (*shell, contaminated_step, *repair, 15, 15, 15)
    repaired = verify(repaired_attempt, challenge, limits)
    assert good["ok"] and repaired["ok"] and bad["code"] == "E_MOVE_NOT_APPLICABLE"
    witness = {
        "challenge_id": challenge["challenge_id"],
        "instance_hash": challenge["instance_hash"],
        "full_stabilized_start": source,
        "rank_preserving_route": route,
        "clean_endpoint": clean_endpoint,
        "contaminated_endpoint": contaminated_endpoint,
        "common_projected_endpoint": project(clean_endpoint),
        "z_exponents_clean_and_contaminated": [
            [word.count(3) - word.count(-3) for word in state]
            for state in [clean_endpoint, contaminated_endpoint]
        ],
        "accepted": {"moves": good_attempt, "verdict": good},
        "rejected": {"moves": bad_attempt, "verdict": bad},
        "repaired": {"moves": repaired_attempt, "verdict": repaired},
        "invisible_contamination": contaminated_step,
        "shortest_invisible_repair": repair,
    }
    if challenge["challenge_id"] == "sac-04359" and route[-1] == 4:
        witness["geodesic_suffix"] = inspect_geodesic_suffix(challenge, source, route, contaminated_step, limits)
    return witness


def toy_ordered(limits):
    start = FULL_TARGET
    shadow = project(start)
    route = (move_id("multiplication", 2, other=0, invert_other=False),
             move_id("multiplication", 0, other=2, invert_other=True))
    trace = path_trace(start, route)
    shadows = [project(state) for state in trace]
    assert path_trace(shadow, route) == shadows
    assert shadows[-1] == ((), (2,), (1,)) and canonical(shadows[-1]) == PROJECTED_TARGET
    assert sum(a != b for a, b in zip(shadow, shadows[-1])) == 2
    fibres = lift_fibres(start, shadows, ordered=True)
    assert fibres["layer_sizes"] == [1, 1, 1] and fibres["successful_lift"] is None
    repair = best_invisible_repair(trace[-1], 3)
    assert repair is not None and len(repair) == 3
    result = {"challenge_id": "toy-ordered-shadow",
              "initial_relators": TARGET_TWO, "target_relators": (),
              "move_spec_version": stable_core.MOVE_SPEC_VERSION}
    rejection = (14, *route, 15, 15, 15)
    repair_path = (14, *route, *repair, 15, 15, 15)
    rejection_verdict = verify(rejection, result, limits)
    repair_verdict = verify(repair_path, result, limits)
    assert rejection_verdict["code"] == "E_MOVE_NOT_APPLICABLE" and repair_verdict["ok"]
    return {
        "ordered_endpoint_distance": 2,
        "unordered_endpoint_distance": 0,
        "projected_move_ids": route,
        "projected_trace": shadows,
        "literal_trace": trace,
        "one_move_per_edge_lift": fibres,
        "shortest_invisible_repair": repair,
        "repair_trace": path_trace(trace[-1], repair),
        "repair_verdict": repair_verdict,
        "rejection_verdict": rejection_verdict,
        "repair_moves": repair_path,
        "rejected_moves": rejection,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--ids", default=" ".join(FRESH))
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--depth", default=36, type=int)
    parser.add_argument("--seeds", default=2, type=int)
    parser.add_argument("--toy-only", action="store_true")
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_SHA
    manifest = json.loads(raw)
    assert len(FULL_MOVES) == 33 and len(PROJECTED_MOVES) == 27
    limits = manifest["limits"]
    results = {"manifest_sha256": MANIFEST_SHA, "toy_ordered": toy_ordered(limits), "runs": []}
    args.output.write_text(json.dumps(results, indent=2) + "\n")
    if args.toy_only:
        return
    challenges = {row["challenge_id"]: row for row in manifest["challenges"]}
    reverse = reverse_rank_two(4)
    for short in args.ids.split():
        challenge = challenges[f"sac-{short}"]
        initial = tuple(map(tuple, challenge["initial_relators"]))
        began = monotonic()
        route = None
        for seed in range(args.seeds):
            route = guided_route(initial, reverse, args.width, args.depth, seed)
            if route is not None:
                break
        run = {"challenge_id": challenge["challenge_id"], "seconds": monotonic() - began,
               "width": args.width, "depth": args.depth, "seeds_used": seed + 1}
        if route is not None:
            run["witness"] = inspect(challenge, initial + ((3,),), route, limits)
        results["runs"].append(run)
        args.output.write_text(json.dumps(results, indent=2) + "\n")
        print(run["challenge_id"], None if route is None else len(route), run["seconds"], flush=True)
        if route is not None:
            return


if __name__ == "__main__":
    main()
