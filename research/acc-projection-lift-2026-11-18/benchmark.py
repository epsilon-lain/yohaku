"""Reproduce the matched ACC projection experiment against the frozen verifier."""

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from time import monotonic

from verifier import stable_core
from verifier.core import free_reduce


LOCK = {
    "data/manifest.json": "dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37",
    "canon.py": "36cc9e6e79c8087ffaa48c50e2643872e8a0eb4ab0e134e601526604d9abf297",
    "core.py": "d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5",
    "stable_core.py": "234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d",
}
PRESERVING = [
    row for row in stable_core.MOVE_TABLE
    if row["inverse"] is not None
    and row["relator"] < 3
    and row.get("other", 0) < 3
    and abs(row.get("conjugator", 0)) <= 3
]
GOAL = ((1,), (2,), (3,))


def encode(state):
    return "".join("".join(str(2 * abs(letter) - (letter > 0)) for letter in word) + "0" for word in state)


def engine_table(projected):
    for row in PRESERVING:
        category = row["category"]
        if category == "inversion":
            kind, argument = 0, 0
        elif category == "multiplication":
            kind, argument = 1 + row["invert_other"], row["other"]
        else:
            conjugator = row["conjugator"]
            if projected and abs(conjugator) == 3:
                continue
            kind, argument = 3, ord(encode(((conjugator,),))[0])
        yield f"{row['id']} {kind} {row['relator']} {argument}"


def projection(state):
    return tuple(free_reduce(tuple(letter for letter in word if abs(letter) != 3)) for word in state)


def apply(state, move):
    child, reason = stable_core.apply_move(state, move)
    if reason is not None:
        raise RuntimeError(f"Official move {move} rejected: {reason}")
    return child


def cohort(manifest):
    rows = {row["challenge_id"]: row for row in manifest["challenges"]
            if row["challenge_id"].startswith("sac-") and row["scored"]}
    for length in (15, 16, 17):
        candidates = [cid for cid, row in rows.items()
                      if sum(map(len, row["initial_relators"])) == length]
        candidates.sort(key=lambda cid: hashlib.sha256(f"yohaku-acc-projection-v1:{cid}".encode()).digest())
        for cid in candidates[:2]:
            yield "fresh", rows[cid]
    for cid in ("sac-04359", "sac-08327"):
        yield "follow_up", rows[cid]
    yield "positive_control", rows["sac-01635"]


def arm(binary, start, projected, args):
    began = monotonic()
    goal = GOAL
    if projected:
        start, goal = projection(start), projection(goal)
    fixture = "\n".join([encode(start), encode(goal), *engine_table(projected)]) + "\n"
    setup_seconds = monotonic() - began
    completed = subprocess.run(
        [str(binary), str(args.states_per_ball), str(args.seconds_per_arm),
         str(args.forward_radius), str(args.reverse_radius)],
        input=fixture, text=True, capture_output=True, timeout=args.seconds_per_arm + 5,
    )
    elapsed = monotonic() - began
    result = {"status": "guard" if completed.returncode else "complete",
              "preprocess_seconds": setup_seconds, "elapsed_including_preprocess_seconds": elapsed}
    if completed.returncode:
        result["guard_detail"] = completed.stderr.splitlines()
        return result
    result.update(json.loads(completed.stdout))
    witness = result["rank_preserving_witness"]
    if witness is not None:
        state = start
        for move in witness:
            state = apply(state, move)
        if sorted(state) != sorted(goal):
            raise RuntimeError("Engine witness failed official-step replay")
    else:
        actions = 27 if projected else 33
        if result["forward_shell_edge_slots"] != result["forward_orbit_layers"][-1] * actions:
            raise RuntimeError("Engine failed to cover complete shell")
    return result


def lift(start, projected_moves):
    """Find every reachable labeled full state along the chosen multiset path."""
    began = monotonic()
    projected_state = projection(start)
    frontier = {start: ()}
    counts = [1]
    first_empty = None
    examined = 0
    for step, projected_move in enumerate(projected_moves, 1):
        projected_state = apply(projected_state, projected_move)
        wanted = tuple(sorted(projected_state))
        following = {}
        for index, (state, prefix) in enumerate(frontier.items()):
            if len(following) > 150_000 or (index % 1024 == 0 and monotonic() - began > 15):
                return {"status": "guard", "frontier_sizes": counts, "examined_moves": examined,
                        "incomplete_depth": step, "elapsed_seconds": monotonic() - began}
            for row in PRESERVING:
                move = row["id"]
                child = apply(state, move)
                examined += 1
                if tuple(sorted(projection(child))) == wanted and child not in following:
                    following[child] = prefix + (move,)
        counts.append(len(following))
        frontier = following
        if not frontier:
            first_empty = step
            break
    lifts = [prefix for state, prefix in frontier.items() if sorted(state) == sorted(GOAL)]
    representative = list(lifts[0]) if lifts else None
    return {
        "status": "lifted" if lifts else "chosen_path_has_no_equal_length_lift",
        "full_preserving_witness": representative,
        "frontier_sizes": counts,
        "first_empty_frontier": first_empty,
        "terminal_fiber_size": len(frontier),
        "terminal_goal_count": len(lifts),
        "examined_moves": examined,
        "elapsed_seconds": monotonic() - began,
    }


def verify(challenge, preserving, limits):
    moves = [14, *preserving, 15, 15, 15]
    verdict = stable_core.verify(challenge, moves, challenge["move_spec_version"], limits)
    if not verdict["ok"]:
        raise RuntimeError(f"Official rejection of reconstructed route: {verdict}")
    return {"moves": moves, **verdict}


def compare(binary, category, challenge, limits, args, ordinal):
    start = tuple(map(tuple, challenge["initial_relators"])) + ((3,),)
    result = {"case": challenge["challenge_id"], "cohort": category,
              "instance_hash": challenge["instance_hash"], "initial_length": sum(map(len, start)) - 1}
    modes = ("direct", "projected") if (ordinal + args.flip_order) % 2 == 0 else ("projected", "direct")
    result["arm_order"] = modes
    for mode in modes:
        result[mode] = arm(binary, start, mode == "projected", args)
    direct = result["direct"]
    projected = result["projected"]
    if direct.get("rank_preserving_witness") is not None:
        direct["certificate"] = verify(challenge, direct["rank_preserving_witness"], limits)
    path = projected.get("rank_preserving_witness")
    if path is not None:
        result["lift"] = lift(start, path)
        reconstructed = result["lift"].get("full_preserving_witness")
        if reconstructed is not None:
            result["lift"]["certificate"] = verify(challenge, reconstructed, limits)
    if direct["status"] == projected["status"] == "complete":
        if projected["distance_lower_bound"] > direct["distance_lower_bound"]:
            raise RuntimeError("Projection increased the bounded distance")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--states-per-ball", type=int, default=1_800_000)
    parser.add_argument("--seconds-per-arm", type=int, default=30)
    parser.add_argument("--forward-radius", type=int, default=4)
    parser.add_argument("--reverse-radius", type=int, default=5)
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--flip-order", action="store_true")
    args = parser.parse_args()
    official = Path(stable_core.__file__).parent
    for file, expected in LOCK.items():
        path = args.manifest if file == "data/manifest.json" else official / file
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise RuntimeError(f"Frozen fixture hash mismatch: {file}")
    manifest = json.loads(args.manifest.read_bytes())
    cases = [(category, challenge) for category, challenge in cohort(manifest)
             if not args.only or challenge["challenge_id"] in args.only]
    if not cases or (args.only and len(cases) != len(set(args.only))):
        raise RuntimeError("Only sample IDs from the preregistered cohort")
    output = {
        "study": "exactly one added generator; both arms search the fixed-rank representation",
        "official_commit": "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e",
        "official_sha256": LOCK,
        "limits": {"max_preserving_distance": args.forward_radius + args.reverse_radius + 1,
                   "forward_radius": args.forward_radius, "reverse_radius": args.reverse_radius,
                   "seconds_per_arm": args.seconds_per_arm, "states_per_ball": args.states_per_ball,
                   "address_space_mib": 460},
        "runs": [],
    }
    for ordinal, (category, challenge) in enumerate(cases):
        result = compare(args.binary.resolve(), category, challenge, manifest["limits"], args, ordinal)
        output["runs"].append(result)
        args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
        print(result["case"], result["direct"].get("distance_lower_bound"),
              result["projected"].get("distance_lower_bound"), result.get("lift", {}).get("status"),
              flush=True)


if __name__ == "__main__":
    main()
