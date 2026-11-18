#!/usr/bin/env python3
"""Look for a shortest projected rank-three path whose endpoint does not lift."""

import argparse
import hashlib
import json
from pathlib import Path
from time import monotonic

from verifier import canon, core, stable_core


MANIFEST_SHA = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"
FULL_MOVES = tuple(
    row["id"] for row in stable_core.MOVE_TABLE
    if row["inverse"] is not None and row["relator"] < 3
    and row.get("other", 0) < 3 and abs(row.get("conjugator", 0)) <= 3
)
PROJECTED_MOVES = tuple(
    move for move in FULL_MOVES if abs(stable_core.MOVE_TABLE[move].get("conjugator", 0)) <= 2
)
PROJECTED_TARGET = ((), (1,), (2,))
FULL_TARGET = ((1,), (2,), (3,))
DEFAULT_IDS = ("01635", "08491", "04416", "07667", "00066", "00626", "09241", "04551",
               "04359", "08327", "09594")


def project(state):
    return tuple(core.free_reduce(tuple(a for a in word if abs(a) != 3)) for word in state)


def canonical(state):
    return tuple(sorted(state))


def move(state, action):
    child, reason = stable_core.apply_move(state, action)
    if reason is not None:
        raise ValueError(f"Illegal action {action}: {reason}")
    return child


def ball(start, radius):
    start = canonical(start)
    interned = {word: word for word in start}
    layers = [[start]]
    distance = {start: 0}
    for depth in range(1, radius + 1):
        upcoming = []
        for state in layers[-1]:
            for action in PROJECTED_MOVES:
                raw = move(state, action)
                child = canonical(interned.setdefault(word, word) for word in raw)
                if child not in distance:
                    distance[child] = depth
                    upcoming.append(child)
        layers.append(upcoming)
    return distance, layers


def shortest_dag(forward_layers, reverse_distances, shortest):
    """Identify all geodesic vertices outside the complete reverse ball."""
    on_path = {}
    for depth in range(len(forward_layers) - 2, -1, -1):
        for state in forward_layers[depth]:
            remaining = shortest - depth
            if state in reverse_distances:
                continue
            for action in PROJECTED_MOVES:
                child = canonical(move(state, action))
                if reverse_distances.get(child, on_path.get(child)) == remaining - 1:
                    on_path[state] = remaining
                    break
    return on_path


def failing_geodesic(start, distances, distance, max_vertices):
    """Search over full states while requiring every projected step to advance a geodesic."""
    seen = {start}
    layer = [(start, ())]
    first_good = None
    for remaining in range(distance, 0, -1):
        upcoming = []
        for state, route in layer:
            shadow = project(state)
            for action in PROJECTED_MOVES:
                if distances.get(canonical(move(shadow, action))) != remaining - 1:
                    continue
                new_state = move(state, action)
                if new_state in seen:
                    continue
                candidate = route + (action,)
                if remaining == 1:
                    if canonical(new_state) != FULL_TARGET:
                        return candidate, first_good, len(seen), True
                    if first_good is None:
                        first_good = candidate
                seen.add(new_state)
                upcoming.append((new_state, candidate))
                if len(seen) >= max_vertices:
                    return None, first_good, len(seen), False
        layer = upcoming
    return None, first_good, len(seen), True


def lift_fibres(start, shadow_path, ordered):
    """Enumerate every one-action-per-edge lift of the given projected vertex sequence."""
    shape = (lambda state: state) if ordered else canonical
    fibres = [{start: ()}]
    for shadow in shadow_path[1:]:
        destination = shape(shadow)
        reached = {}
        for state, prefix in fibres[-1].items():
            for action in FULL_MOVES:
                child = move(state, action)
                if shape(project(child)) == destination:
                    reached.setdefault(child, prefix + (action,))
        fibres.append(reached)
    accepted = next((moves for state, moves in fibres[-1].items() if canonical(state) == FULL_TARGET), None)
    return {
        "layer_sizes": [len(layer) for layer in fibres],
        "final_fibre": sorted(fibres[-1]),
        "successful_lift": accepted,
    }


def path_trace(start, actions):
    states = [start]
    for action in actions:
        states.append(move(states[-1], action))
    return states


def verify(route, challenge, limits):
    return stable_core.verify(challenge, list(route), stable_core.MOVE_SPEC_VERSION, limits)


def inspect_bad_route(challenge, start, route, limits):
    trace = path_trace(start, route)
    projected = path_trace(project(start), route)
    assert [project(state) for state in trace] == projected
    assert canonical(projected[-1]) == PROJECTED_TARGET
    z_exponents = [[word.count(3) - word.count(-3) for word in state] for state in trace]
    deletions = [15 + index for index, word in enumerate(projected[-1]) if word]
    delete_all = [15, 15, 15]
    return {
        "projected_moves": route,
        "projected_trace": projected,
        "full_trace": trace,
        "fresh_generator_exponents": z_exponents,
        "labelled_fibres": lift_fibres(start, projected, ordered=True),
        "unlabelled_fibres": lift_fibres(start, projected, ordered=False),
        "direct_deletion_order": delete_all,
        "official_deletion_attempt": verify([14, *route, *delete_all], challenge, limits),
        "projected_nonempty_slots": deletions,
    }


def scan(challenge, reverse_distances, forward_radius, max_vertices, limits):
    began = monotonic()
    start = tuple(map(tuple, challenge["initial_relators"])) + ((3,),)
    forward_distances, forward_layers = ball(project(start), forward_radius)
    distance = min((f + reverse_distances[state] for state, f in forward_distances.items()
                    if state in reverse_distances), default=None)
    result = {
        "challenge_id": challenge["challenge_id"],
        "instance_hash": challenge.get("instance_hash"),
        "full_start": start,
        "exact_forward_layers": list(map(len, forward_layers)),
        "projected_distance": distance,
    }
    if distance is not None:
        path_distances = shortest_dag(forward_layers, reverse_distances, distance)
        assert reverse_distances.get(canonical(project(start)), path_distances.get(canonical(project(start)))) == distance
        bad, good, count, complete = failing_geodesic(
            start, reverse_distances | path_distances, distance, max_vertices)
        result.update(geodesic_lift_states=count, geodesic_scan_complete=complete)
        if good is not None:
            route = [14, *good, 15, 15, 15]
            result.update(official_successful_moves=route, official_verdict=verify(route, challenge, limits))
            assert result["official_verdict"]["ok"]
        if bad is not None:
            result["failed_lift"] = inspect_bad_route(challenge, start, bad, limits)
    result["seconds"] = round(monotonic() - began, 6)
    return result


def reverse_lift_witness(distances, radius, limits):
    """Scan geodesics from the target for any projected rank-two start with a polluted lift."""
    layer = [FULL_TARGET]
    for depth in range(1, radius + 1):
        following = set()
        for state in layer:
            shadow = project(state)
            for action in PROJECTED_MOVES:
                child_shadow = canonical(move(shadow, action))
                if distances.get(child_shadow) != depth:
                    continue
                child = canonical(move(state, action))
                if child_shadow[0] == () and child != (child_shadow[1], child_shadow[2], (3,)):
                    # The lifted reverse route has a different endpoint from the genuine stabilization.
                    relators = child_shadow[1:]
                    start = relators + ((3,),)
                    route, _, count, complete = failing_geodesic(start, distances, depth, 100_000)
                    if route is None:
                        raise RuntimeError(f"Reverse witness failed replay: {child} {depth} {count} {complete}")
                    challenge = {"challenge_id": "toy-lift-audit", "initial_relators": relators,
                                 "target_relators": (), "move_spec_version": stable_core.MOVE_SPEC_VERSION}
                    return {"toy": True, "projected_distance": depth, "start": start,
                            "failed_lift": inspect_bad_route(challenge, start, route, limits)}
                following.add(child)
        layer = sorted(following)
        print(f"toy backtracking radius {depth}: {len(layer)} full states", flush=True)
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--ids", default=" ".join(DEFAULT_IDS))
    parser.add_argument("--reverse", default=5, type=int)
    parser.add_argument("--forward", default=4, type=int)
    parser.add_argument("--max-geodesic-states", default=10000, type=int)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--toy", action="store_true")
    args = parser.parse_args()
    raw = args.manifest.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == MANIFEST_SHA
    manifest = json.loads(raw)
    move_hash = canon.move_spec_hash(stable_core.MOVE_TABLE)
    assert len(FULL_MOVES) == 33 and len(PROJECTED_MOVES) == 27
    assert set(PROJECTED_MOVES) == {stable_core.INVERSE_MOVE[action] for action in PROJECTED_MOVES}
    challenges = {row["challenge_id"]: row for row in manifest["challenges"] if row["challenge_id"].startswith("sac-")}
    reverse_distances, reverse_layers = ball(PROJECTED_TARGET, args.reverse)
    result = {
        "manifest_sha256": MANIFEST_SHA,
        "stable_move_spec_hash": move_hash,
        "reverse_radii_layers": list(map(len, reverse_layers)),
        "forward_radius": args.forward,
        "projected_move_ids": PROJECTED_MOVES,
        "full_move_ids": FULL_MOVES,
        "results": [],
    }
    if args.toy:
        result["toy"] = reverse_lift_witness(reverse_distances, args.reverse, manifest["limits"])
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        return
    ids = args.ids.split()
    if ids == ["short"]:
        ids = [cid for cid, row in sorted(challenges.items(), key=lambda row: (sum(map(len, row[1]["initial_relators"])), row[0]))
               if sum(map(len, row["initial_relators"])) <= 17 and cid != "sac-07445"]
    for short in ids:
        cid = short if short.startswith("sac-") else f"sac-{short}"
        challenge = challenges[cid]
        assert challenge["instance_hash"] == canon.instance_hash(
            cid, challenge["generators"], challenge["initial_relators"], challenge["target_relators"],
            challenge["move_spec_version"], move_hash,
        )
        case = scan(challenge, reverse_distances, args.forward, args.max_geodesic_states, manifest["limits"])
        result["results"].append(case)
        args.output.write_text(json.dumps(result, indent=2) + "\n")
        print(cid, case["projected_distance"], "failed_lift" in case, case["seconds"], flush=True)
        if "failed_lift" in case:
            break


if __name__ == "__main__":
    main()
