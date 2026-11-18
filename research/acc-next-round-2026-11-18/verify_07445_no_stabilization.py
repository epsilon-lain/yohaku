import argparse
import hashlib
import json
import sys
import time
import types
from functools import cache
from pathlib import Path


COMMIT = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
OFFICIAL_BLOBS = {
    "canon": "93175152acd876566ff60bbfaf7cd90cd8cd2fa9",
    "core": "0a5da5fe6e3e42c96877734dad46b155a69c02b2",
}
MANIFEST_SHA256 = "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37"
MAX_CALLS = 325_000
MAX_SEEN_PER_BALL = 150_000
MAX_SECONDS = 12


class Guard(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def word_state(relators):
    return tuple(tuple(word) for word in relators)


def complete_layers(root, radius, move, move_ids):
    seen = {root}
    layers = [{root}]
    for _ in range(radius):
        following = set()
        for state in sorted(layers[-1]):
            for move_id in move_ids:
                child = move(state, move_id)
                if child not in seen:
                    if len(seen) >= MAX_SEEN_PER_BALL:
                        raise Guard("ball state cap")
                    seen.add(child)
                    following.add(child)
        layers.append(following)
    return seen, layers


def word_ball_digest(layer):
    codes = {-2: 1, -1: 2, 1: 3, 2: 4}
    ordered = sorted(bytes(codes[x] for x in first) + b"\x00" + bytes(codes[x] for x in second)
                     for first, second in layer)
    check = hashlib.sha256()
    for state in ordered:
        check.update(len(state).to_bytes(4, "big"))
        check.update(state)
    return check.hexdigest()


def exponent(word):
    return (word.count(1) - word.count(-1), word.count(2) - word.count(-2))


def changed_exponent(row, matrix):
    current = matrix[row["relator"]]
    match row["category"]:
        case "inversion":
            return (-current[0], -current[1])
        case "multiplication":
            other = matrix[row["other"]]
            sign = -1 if row["invert_other"] else 1
            return (current[0] + sign * other[0], current[1] + sign * other[1])
        case "conjugation":
            return current
    raise ValueError(row)


def product(left, right):
    a, b, c, d = left
    e, f, g, h = right
    return ((a*e+b*g) % 1009, (a*f+b*h) % 1009,
            (c*e+d*g) % 1009, (c*f+d*h) % 1009)


def inverse(matrix):
    a, b, c, d = matrix
    return (d, -b % 1009, -c % 1009, a)


GENERATORS = {1: (1, 2, 0, 1), 2: (1, 0, 2, 1)}
GENERATORS.update({-g: inverse(value) for g, value in list(GENERATORS.items())})


@cache
def fingerprint(word):
    result = (1, 0, 0, 1)
    for letter in word:
        result = product(result, GENERATORS[letter])
    return result


def changed_fingerprint(row, word, other):
    match row["category"]:
        case "inversion":
            return inverse(fingerprint(word))
        case "multiplication":
            donor = fingerprint(other)
            return product(fingerprint(word), inverse(donor) if row["invert_other"] else donor)
        case "conjugation":
            letter = row["conjugator"]
            return product(product(GENERATORS[letter], fingerprint(word)), GENERATORS[-letter])
    raise ValueError(row)


def midpoint_intersections(forward, reverse, base_projections, move, rows, check_time):
    # An exact midpoint has one one-step predecessor in each depth-five layer.
    # These indices record necessary pairs: unchanged word and new exponent.
    frontier_projections = [set(), set()]
    for index, state in enumerate(forward):
        if index % 1024 == 0:
            check_time()
        sums = tuple(map(exponent, state))
        for slot in (0, 1):
            x, y = sums[slot]
            z, w = sums[1-slot]
            stationary = state[1-slot]
            frontier_projections[slot].update((stationary, pair) for pair in (
                (x, y), (-x, -y), (x+z, y+w), (x-z, y-w)))
    weak_projections = [{(fingerprint(word), powers) for word, powers in projected}
                        for projected in frontier_projections]
    slot_rows = [[row for row in rows if row["relator"] == slot] for slot in (0, 1)]
    exact_candidates = set()
    reverse_calls = 0
    forward_calls = 0
    hits = set()
    for index, state in enumerate(sorted(reverse)):
        if index % 512 == 0:
            check_time()
        sums = tuple(map(exponent, state))
        for row in rows:
            slot = row["relator"]
            other = 1-slot
            powers = changed_exponent(row, sums)
            same_slot = (state[other], powers) in frontier_projections[slot]
            if not same_slot and (changed_fingerprint(row, state[slot], state[other]), sums[other]) not in weak_projections[other]:
                continue
            midpoint = move(state, row["id"])
            reverse_calls += 1
            if midpoint in exact_candidates:
                continue
            exact_candidates.add(midpoint)
            middle_sums = tuple(map(exponent, midpoint))
            for affected in (0, 1):
                stationary = midpoint[1-affected]
                if (stationary, middle_sums[affected]) not in frontier_projections[affected]:
                    continue
                for inverse_row in slot_rows[affected]:
                    if (stationary, changed_exponent(inverse_row, middle_sums)) not in base_projections[affected]:
                        continue
                    predecessor = move(midpoint, inverse_row["id"])
                    forward_calls += 1
                    if predecessor in forward:
                        hits.add(midpoint)
    return dict(candidate_reverse_edges=len(reverse)*len(rows), distinct_checked_midpoints=len(exact_candidates),
                reverse_official_apply_calls=reverse_calls, forward_official_apply_calls=forward_calls,
                intersections=len(hits), exact_projection_sizes=list(map(len, frontier_projections)))


def load_core(verifier):
    package = "_fixed_acc_verifier"
    sys.modules[package] = types.ModuleType(package)
    sys.modules[package].__path__ = [str(verifier)]
    for name, expected in OFFICIAL_BLOBS.items():
        path = verifier / f"{name}.py"
        source = path.read_bytes()
        header = f"blob {len(source)}\0".encode()
        assert hashlib.sha1(header + source).hexdigest() == expected
        qualified = f"{package}.{name}"
        module = types.ModuleType(qualified)
        module.__package__ = package
        sys.modules[qualified] = module
        exec(compile(source, str(path), "exec"), module.__dict__)
    return sys.modules[f"{package}.core"]


def main():
    parser = argparse.ArgumentParser(description="Check the swapped rank-two target through depth 12.")
    parser.add_argument("--official-root", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    verifier = args.official_root / "competition/tools/verifier"
    core = load_core(verifier)
    manifest_bytes = (verifier / "data/manifest.json").read_bytes()
    assert digest(manifest_bytes) == MANIFEST_SHA256
    manifest = json.loads(manifest_bytes)
    by_id = {entry["challenge_id"]: entry for entry in manifest["challenges"]}
    ac = by_id["ac-07445"]
    stable = by_id["sac-07445"]
    start = word_state(stable["initial_relators"])
    assert start == word_state(ac["initial_relators"])
    assert ac["scored"] and stable["scored"]
    ordinary_target = word_state(ac["target_relators"])
    assert ordinary_target == ((1,), (2,))
    swapped_target = ordinary_target[::-1]
    move_ids = tuple(row["id"] for row in core.MOVE_TABLE)

    calls = 0

    def check_time():
        if time.monotonic() - started >= MAX_SECONDS:
            raise Guard("wall time cap")

    def move(state, move_id):
        nonlocal calls
        if calls >= MAX_CALLS:
            raise Guard("official apply cap")
        if calls % 1024 == 0:
            check_time()
        calls += 1
        return core.apply_move(state, move_id)

    record = dict(upstream_commit=COMMIT, stable_challenge=stable["challenge_id"],
                  stable_instance_hash=stable["instance_hash"], start=start,
                  swapped_target=swapped_target, maximum_seconds=MAX_SECONDS,
                  maximum_official_apply_calls=MAX_CALLS, maximum_states_per_ball=MAX_SEEN_PER_BALL)
    try:
        forward, forward_layers = complete_layers(start, 5, move, move_ids)
        forward_counts = [len(layer) for layer in forward_layers]
        forward_digests = [word_ball_digest(layer) for layer in forward_layers]
        record["forward_5"] = dict(states=len(forward), layers=forward_counts,
                                   layer_state_sha256=forward_digests, official_apply_calls=calls)

        before = calls
        reverse, reverse_layers = complete_layers(swapped_target, 5, move, move_ids)
        record["inverse_5"] = dict(states=len(reverse), layers=list(map(len, reverse_layers)),
                                   official_apply_calls=calls-before)

        intersections = forward & reverse
        record["intersections_within_5_plus_5"] = len(intersections)
        if intersections:
            raise ValueError("existing balls intersect")

        # Any one-step neighbor in the forward ball shares the unchanged slot
        # verbatim and has the required exponent pair in the changed slot.
        forward_projections = [set(), set()]
        for first, second in forward:
            forward_projections[0].add((second, exponent(first)))
            forward_projections[1].add((first, exponent(second)))

        before = calls
        screened = 0
        matches = set()
        r6_max = 0
        for index, state in enumerate(sorted(reverse_layers[-1])):
            if index % 512 == 0:
                check_time()
            matrix = tuple(map(exponent, state))
            for row in core.MOVE_TABLE:
                changed = row["relator"]
                required = (state[1-changed], changed_exponent(row, matrix))
                if required not in forward_projections[changed]:
                    screened += 1
                    continue
                child = move(state, row["id"])
                assert exponent(child[changed]) == required[1] and child[1-changed] == required[0]
                r6_max = max(r6_max, sum(map(len, child)))
                if child in forward:
                    matches.add(child)
        considered = len(reverse_layers[-1])*len(move_ids)
        assert screened + calls-before == considered
        record["inverse_6_shell"] = dict(candidate_edges=considered, necessary_filter_rejections=screened,
                                         official_apply_calls=calls-before, intersections=len(matches),
                                         maximum_evaluated_total_word_length=r6_max)
        if matches:
            raise ValueError("a path to the swapped target needs exact witness replay")
        record["conclusion"] = dict(
            swapped_target_excluded_through=11,
            stable_without_additions_distance_interval=[14, 15],
            condition="Exact rank-two ordinary actions until first deletion, without stabilization anywhere; the known ordered target distance is 13.",
        )
        shell = midpoint_intersections(forward_layers[-1], reverse_layers[-1], forward_projections,
                                       move, core.MOVE_TABLE, check_time)
        record["both_depth_6_shells"] = shell
        if not shell["intersections"]:
            record["conclusion"]["swapped_target_excluded_through"] = 12
            record["conclusion"]["stable_without_additions_distance_interval"] = [15, 15]
        record["status"] = "complete"
    except Guard as error:
        record["status"] = "incomplete"
        record["guard"] = str(error)

    record["official_apply_calls"] = calls
    record["seconds"] = time.monotonic() - started
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
