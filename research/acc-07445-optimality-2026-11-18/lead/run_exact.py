#!/usr/bin/env python3
"""Build and run the labeled exact one-add experiment from the frozen verifier."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import resource
import subprocess
import sys
import tempfile
import time
import types


HERE = Path(__file__).resolve().parent
COMMIT = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
FILES = {
    "canon.py": ("36cc9e6e79c8087ffaa48c50e2643872e8a0eb4ab0e134e601526604d9abf297",
                 "93175152acd876566ff60bbfaf7cd90cd8cd2fa9"),
    "core.py": ("d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5",
                "0a5da5fe6e3e42c96877734dad46b155a69c02b2"),
    "stable_core.py": ("234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d",
                       "af48e32f766dbcd0cad0becd8c1c4edb4358efac"),
    "data/manifest.json": ("dc8587d7dc6855edfb8aad087f27f4db59c558f66bdf838b664c1634a357ad37",
                           "accdb626ee08a06beea3f88dc7f351514c99eb27"),
}

START = ((-2, -2, 1, 2, 1), (-2, -2, -1, 2, 1, 2, -1))
INSTANCE = "sha256:f704cfdedbc0b2205b6af5e0aaff9de3ea51826121e55252dcd72ecbf7637477"
BASELINE = [6, 4, 12, 1, 3, 6, 12, 2, 5, 6, 4, 2, 4, 16, 15]


def load_fixed_verifier(root):
    path = root / "competition/tools/verifier"
    verified = {}
    package = "_lead_fixed_stable_verifier"
    module = types.ModuleType(package)
    module.__path__ = []
    sys.modules[package] = module
    for filename, (expected_digest, expected_blob) in FILES.items():
        source = (path / filename).read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        blob = hashlib.sha1(f"blob {len(source)}\0".encode() + source).hexdigest()
        if (digest, blob) != (expected_digest, expected_blob):
            raise ValueError(f"official source mismatch for {filename}")
        verified[filename] = {"sha256": digest, "git_blob": blob}
        if filename.endswith(".json"):
            manifest = json.loads(source)
        else:
            qualified = f"{package}.{filename.removesuffix('.py')}"
            module = types.ModuleType(qualified)
            module.__package__ = package
            sys.modules[qualified] = module
            exec(compile(source, str(path / filename), "exec"), module.__dict__)
    challenge = next(entry for entry in manifest["challenges"] if entry["challenge_id"] == "sac-07445")
    assert challenge["scored"] is True
    assert challenge["instance_hash"] == INSTANCE
    assert tuple(map(tuple, challenge["initial_relators"])) == START
    assert challenge["target_relators"] == []
    assert challenge["move_spec_version"] == "sac-r8-v1"
    assert manifest["limits"] == {"max_path_length": 100000, "max_total_relator_length": 10000, "max_work": 5000000}
    return module, challenge, manifest["limits"], verified


def encode_letter(letter):
    return letter if letter > 0 else 4 - letter


def encode_state(state):
    return " ".join("".join(str(encode_letter(letter)) for letter in word) or "_" for word in state)


def preserving_rows(core):
    codes = {"inversion": "I", "multiplication": "M", "conjugation": "C"}
    pairs = []
    for row in core.MOVE_TABLE:
        if row["category"] not in codes or row["relator"] >= 3:
            continue
        code = codes[row["category"]]
        if code == "M":
            argument = row["other"]
            if argument >= 3:
                continue
        elif code == "C":
            conjugator = row["conjugator"]
            if abs(conjugator) > 3:
                continue
            argument = encode_letter(conjugator)
        else:
            argument = -1
        pairs.append((row["id"], code, row["relator"], argument, int(row.get("invert_other", False)), row["inverse"]))
    assert len(pairs) == 33
    return pairs


def trace(core, challenge, limits, moves):
    result = core.verify(challenge, moves, challenge["move_spec_version"], limits)
    assert result["ok"], result
    state = START
    states = [state]
    for move in moves:
        state, reason = core.apply_move(state, move)
        assert reason is None
        states.append(state)
    assert state == ()
    sizes = [sum(map(len, state)) for state in states]
    ranks = list(map(len, states))
    assert sum(sizes) == result["work"] and max(sizes) == result["peak_total_relator_length"]
    return {"moves": moves, "official_verdict": result, "ranks": ranks, "total_lengths": sizes, "trajectory": states}


def cross_check(executable, prefix, rows, core):
    source = random.Random(7445)
    states = []
    roots = [START + ((3,),), ((1,), (2,), (3,)), ((), (1, -2), (3,))]
    for root in roots:
        state = root
        for _ in range(24):
            states.append(state)
            state, reason = core.apply_move(state, source.choice(rows)[0])
            assert reason is None
    inputs = []
    expected = []
    for state in states:
        for move_id, _, slot, _, _, _ in rows:
            result, reason = core.apply_move(state, move_id)
            assert reason is None
            inputs.append(f"{move_id} {encode_state(state)}")
            expected.append(encode_state((result[slot],)))
    check = subprocess.run([str(executable), "--probe"], input=prefix + "\n".join(inputs) + "\n",
                           text=True, capture_output=True, check=True, timeout=6)
    assert check.stdout.splitlines() == expected
    return len(expected)


def directed_calibration(core):
    """Small exact balls in the original graph, with add count in each key."""
    normal = [tuple(row for row in core.MOVE_TABLE if row["inverse"] is not None
                    and row["relator"] < rank and row.get("other", -1) < rank
                    and abs(row.get("conjugator", 0)) <= rank)
              for rank in range(4)]
    inverse_delete_checks = 0
    inverse_add_checks = 0

    def neighbors(state, adds, backward):
        nonlocal inverse_delete_checks, inverse_add_checks
        rank = len(state)
        for row in normal[rank]:
            child, reason = core.apply_move(state, row["inverse"] if backward else row["id"])
            assert reason is None
            yield (child, adds)
        if not backward:
            for slot in range(rank):
                child, reason = core.apply_move(state, 15 + slot)
                if reason is None:
                    yield (child, adds)
            if adds == 0 and rank < 3:
                child, reason = core.apply_move(state, 14)
                assert reason is None
                yield (child, 1)
            return

        if rank < 3:
            for generator in range(1, rank + 2):
                signed_lift = {letter: letter + (letter >= generator) for letter in range(1, rank + 1)}
                signed_lift.update({-letter: -image for letter, image in tuple(signed_lift.items())})
                lifted = tuple(tuple(signed_lift[letter] for letter in word) for word in state)
                for slot in range(rank + 1):
                    previous = lifted[:slot] + ((generator,),) + lifted[slot:]
                    assert core.apply_move(previous, 15 + slot) == (state, None)
                    inverse_delete_checks += 1
                    yield (previous, adds)
        if adds == 0 and rank and state[-1] == (rank,) and all(
                abs(letter) < rank for word in state[:-1] for letter in word):
            previous = state[:-1]
            assert core.apply_move(previous, 14) == (state, None)
            inverse_add_checks += 1
            yield (previous, 1)

    def ball(source, radius, backward):
        frontier = {(source, 0)}
        seen = set(frontier)
        layers = [len(frontier)]
        for _ in range(radius):
            frontier = {child for state, adds in frontier for child in neighbors(state, adds, backward)} - seen
            seen.update(frontier)
            layers.append(len(frontier))
        return seen, layers

    forward, forward_layers = ball(START, 3, False)
    reverse, reverse_layers = ball((), 5, True)
    intersections = sum((state, 1 - adds) in reverse for state, adds in forward)
    assert intersections == 0
    return {"forward_layers": forward_layers, "reverse_layers": reverse_layers,
            "inverse_delete_official_checks": inverse_delete_checks,
            "inverse_add_official_checks": inverse_add_checks,
            "complementary_add_count_intersections": intersections}


def restrict_process():
    resource.setrlimit(resource.RLIMIT_AS, (340_000_000, 340_000_000))
    resource.setrlimit(resource.RLIMIT_CPU, (24, 25))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, default=HERE.parents[1] / "ac_official")
    parser.add_argument("--output", type=Path, default=HERE / "exact-results.json")
    parser.add_argument("--radius", choices=(0, 1, 2, 3, 4), type=int, default=4)
    parser.add_argument("--states", type=int, default=2_000_000)
    parser.add_argument("--seconds", type=float, default=22)
    parser.add_argument("--rss-kib", type=int, default=295_000)
    args = parser.parse_args()
    if not 0 < args.seconds <= 23 or not 6 < args.states <= 2_000_000 or not 0 < args.rss_kib <= 295_000:
        parser.error("require seconds in (0,23], states in (6,2,000,000], and RSS KiB in (0,295,000]")
    started = time.monotonic()
    core, challenge, limits, verified = load_fixed_verifier(args.official_root)
    baseline = trace(core, challenge, limits, BASELINE)
    assert baseline["official_verdict"]["length"] == 15 and baseline["official_verdict"]["work"] == 128
    stable_start, reason = core.apply_move(START, 14)
    assert reason is None and stable_start == START + ((3,),)
    calibration = directed_calibration(core)
    rows = preserving_rows(core)
    table = "\n".join(" ".join(map(str, row)) for row in rows)
    prefix = f"{args.states} {args.seconds} {args.rss_kib} {args.radius}\n{table}\n"
    source = HERE / "rank3_search.cpp"
    with tempfile.TemporaryDirectory(prefix="sac07445-exact-") as temp:
        executable = Path(temp) / "search"
        subprocess.run(["c++", "-std=c++20", "-O3", "-Wall", "-Wextra", "-Wpedantic",
                        str(source), "-o", str(executable)], check=True, timeout=9)
        checked = cross_check(executable, prefix, rows, core)
        child = subprocess.run([str(executable)], input=prefix + encode_state(stable_start) + "\n",
                               text=True, capture_output=True, timeout=24, preexec_fn=restrict_process)
    print(child.stderr, end="", file=sys.stderr)
    if child.returncode:
        raise RuntimeError(f"search exited {child.returncode}: {child.stderr}")
    search = json.loads(child.stdout)
    witness = None
    moves = search["preserving_witness"]
    if moves:
        assert len(moves) <= 10 and all(move in {row[0] for row in rows} for move in moves)
        witness = trace(core, challenge, limits, [14, *moves, 15, 15, 15])
        assert witness["moves"].count(14) == 1 and max(witness["ranks"]) == 3
        assert sum(a > b for a, b in zip(witness["ranks"], witness["ranks"][1:])) == 3
    complete_preserving_bound = None
    if not witness and search["stored_join_complete"]:
        complete_preserving_bound = search["forward"]["complete_radius"] + search["reverse"]["complete_radius"]
        if search["shell_complete"]:
            complete_preserving_bound += 2
    result = {
        "experiment": "exact labeled rank-three preserving graph",
        "official_commit": COMMIT,
        "challenge": challenge,
        "official_files": verified,
        "official_move_probe_comparisons": checked,
        "original_directed_calibration": calibration,
        "rank3_start": stable_start,
        "target_set": "all six permutations of the three positive singleton relators",
        "baseline_no_add": baseline,
        "prior_no_add_minimum": 15,
        "parameters": {"stored_radius_each_side": args.radius, "stored_state_cap": args.states,
                       "wall_seconds_cap": args.seconds, "rss_kib_cap": args.rss_kib,
                       "hard_address_space_bytes": 340_000_000, "hard_cpu_seconds": 25},
        "search": search,
        "complete_preserving_negative_bound": complete_preserving_bound,
        "one_add_paths_excluded_through": (min(14, complete_preserving_bound + 4)
                                           if complete_preserving_bound is not None else None),
        "official_witness": witness,
        "sources": {file.name: hashlib.sha256(file.read_bytes()).hexdigest()
                    for file in [source, Path(__file__)]},
        "elapsed_seconds": time.monotonic() - started,
    }
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({key: result[key] for key in ("search", "one_add_paths_excluded_through",
                                                  "official_witness", "elapsed_seconds")}, indent=2))


if __name__ == "__main__":
    main()
