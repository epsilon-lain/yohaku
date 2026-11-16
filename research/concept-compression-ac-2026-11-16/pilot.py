"""Bounded AC search with fully expanded, honestly charged macro actions.

Python >=3.10, standard library. Official code/data stay in a separate checkout.
No known training solutions are read. This is a heuristic pilot, not an AC proof.
"""
from __future__ import annotations

import argparse
import hashlib
import heapq
import itertools
import json
from pathlib import Path
import sys
import time

TARGET = ((1,), (2,))
INVERSE = (0, 1, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10, 13, 12)
GENERATORS = (1, -1, 2, -2)
COMMIT = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"


def reduce_word(word):
    out = []
    for letter in word:
        if out and out[-1] == -letter:
            out.pop()
        else:
            out.append(letter)
    return tuple(out)


def inverse_word(word):
    return tuple(-a for a in reversed(word))


def apply(state, move):
    """Independent implementation of the published ac-r2-v1 table."""
    a, b = state
    if move < 2:
        return (inverse_word(a), b) if move == 0 else (a, inverse_word(b))
    if move < 6:
        i = (move - 2) // 2
        other = state[1 - i]
        tail = other if move % 2 == 0 else inverse_word(other)
        result = reduce_word(state[i] + tail)
    elif move < 14:
        i = (move - 6) // 4
        g = GENERATORS[(move - 6) % 4]
        result = reduce_word((g,) + state[i] + (-g,))
    else:
        raise ValueError(move)
    return (result, b) if i == 0 else (a, result)


def total_length(state):
    return len(state[0]) + len(state[1])


def target_ball(depth, official_apply=None):
    """Unpruned BFS: every state at distance <=depth from the exact target."""
    suffix = {TARGET: ()}
    frontier = [TARGET]
    sizes = [1]
    evaluations = 0
    peak = 2
    for _ in range(depth):
        following = []
        for state in frontier:
            for move in range(14):
                successor = apply(state, move)
                evaluations += 1
                if official_apply is not None:
                    assert successor == official_apply(state, move)
                peak = max(peak, total_length(successor))
                if successor not in suffix:
                    suffix[successor] = (INVERSE[move],) + suffix[state]
                    following.append(successor)
        frontier = following
        sizes.append(len(frontier))
    return suffix, {"depth": depth, "frontier_sizes": sizes,
                    "states": len(suffix), "primitive_evaluations": evaluations,
                    "peak_total_length": peak, "length_pruning": False,
                    "global_shortest_within_ball": True}


def macro_actions(state):
    """State-derived cyclic trims plus four fixed left-multiplication rules.

    Trimming uses word inspection only; all transitions are evaluated/charged by
    search(). Left multiplication r_i <- r_j^(+/-1) r_i expands into 3 moves.
    The library is fixed before searching and does not use training solutions.
    """
    actions = []
    for i, word in enumerate(state):
        trim = []
        left, right = 0, len(word) - 1
        while left < right and word[left] == -word[right]:
            conjugator = -word[left]
            trim.append(6 + 4 * i + GENERATORS.index(conjugator))
            left += 1
            right -= 1
        if len(trim) > 1:
            actions.append(("cyclic-trim-r" + str(i), tuple(trim)))
    actions.extend((("left-r0-by-r1", (0, 3, 0)),
                    ("left-r0-by-inverse-r1", (0, 2, 0)),
                    ("left-r1-by-r0", (1, 5, 1)),
                    ("left-r1-by-inverse-r0", (1, 4, 1))))
    return actions


def search(start, suffix, variant, budget, length_cap):
    """Identical greedy state priority; macro arm prepends expanded actions.

    Both arms retain every primitive action. Every apply(), including repeated
    or later-discarded transitions, counts against the same per-case budget.
    Search caps and greedy priority mean returned paths are upper bounds only.
    """
    started = time.perf_counter()
    serial = itertools.count()
    queue = [(total_length(start), 0, next(serial), start, ())]
    best = {start: 0}
    counts = {"primitive_evaluations": 0, "expanded_states": 0,
              "length_pruned": 0, "macro_attempts": 0, "macro_steps": 0,
              "duplicate_or_nonimproving": 0}

    def finish(path, status, **extra):
        return {"status": status, "moves": list(path) if path is not None else None,
                "expanded_move_length": len(path) if path is not None else None,
                **counts, "seen_states": len(best),
                "wall_seconds": time.perf_counter() - started, **extra}

    while queue:
        _, distance, _, state, prefix = heapq.heappop(queue)
        if best.get(state) != distance:
            continue
        if state in suffix:
            return finish(prefix + suffix[state], "solved", suffix_length=len(suffix[state]))
        counts["expanded_states"] += 1
        actions = macro_actions(state) if variant == "macro" else []
        actions += [("primitive", (m,)) for m in range(14)]
        for name, action in actions:
            is_macro = name != "primitive"
            if is_macro:
                counts["macro_attempts"] += 1
            successor, extended = state, prefix
            valid = True
            for move in action:
                if counts["primitive_evaluations"] >= budget:
                    return finish(None, "budget_exhausted")
                successor = apply(successor, move)
                counts["primitive_evaluations"] += 1
                counts["macro_steps"] += int(is_macro)
                extended += (move,)
                if total_length(successor) > length_cap:
                    counts["length_pruned"] += 1
                    valid = False
                    break
                if successor in suffix:
                    return finish(extended + suffix[successor], "solved",
                                  suffix_length=len(suffix[successor]),
                                  finishing_action=name)
            if not valid:
                continue
            new_distance = len(extended)
            if new_distance >= best.get(successor, 10**9):
                counts["duplicate_or_nonimproving"] += 1
                continue
            best[successor] = new_distance
            heapq.heappush(queue, (total_length(successor), new_distance,
                                  next(serial), successor, extended))
    return finish(None, "frontier_exhausted")


def read_manifest(path):
    return json.loads(path.read_text(encoding="utf-8"))


def official_verify(root, manifest, submission, output):
    import subprocess
    command = [sys.executable, "-m", "verifier", "--manifest", str(manifest),
               "--submission", str(submission), "--pretty"]
    import os
    environment = dict(os.environ, PYTHONPATH=str(root / "competition/tools"))
    result = subprocess.run(command, capture_output=True, text=True, env=environment)
    output.write_text(result.stdout, encoding="utf-8")
    if result.returncode != 0:
        raise RuntimeError(f"official verification failed: {result.stderr or result.stdout}")
    receipt = json.loads(result.stdout)
    assert receipt["accepted"] is True
    assert all(r["ok"] is True for r in receipt["results"])
    return len(receipt["results"])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--budget", type=int, default=20000)
    parser.add_argument("--length-cap", type=int, default=32)
    parser.add_argument("--target-depth", type=int, default=4)
    args = parser.parse_args()
    root = args.official_root.resolve()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    lock = json.loads(Path(__file__).with_name("upstream-lock.json").read_text())
    assert lock["commit"] == COMMIT
    for entry in lock["files"]:
        data = (root / entry["path"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != entry["sha256"]:
            raise SystemExit("Official source hash mismatch: " + entry["path"])
    sys.path.insert(0, str(root / "competition/tools"))
    from verifier.core import apply_move, verify
    ball, ball_report = target_ball(args.target_depth, apply_move)
    official_file = root / "competition/tools/verifier/data/manifest.json"
    training_file = root / "competition/examples/training_manifest.json"
    official = read_manifest(official_file)
    training = read_manifest(training_file)
    train_cases = sorted((c for c in training["challenges"]
                          if c["move_spec_version"] == "ac-r2-v1"),
                         key=lambda c: c["challenge_id"])[:8]
    formal_cases = sorted((c for c in official["challenges"]
                           if c["move_spec_version"] == "ac-r2-v1"),
                          key=lambda c: (sum(map(len, c["initial_relators"])),
                                         c["challenge_id"]))[:8]
    report = {"official_commit": COMMIT,
              "official_manifest_sha256": hashlib.sha256(official_file.read_bytes()).hexdigest(),
              "training_manifest_sha256": hashlib.sha256(training_file.read_bytes()).hexdigest(),
              "configuration": {"per_case_per_arm_primitive_budget": args.budget,
                                "search_total_length_cap": args.length_cap,
                                "case_selection": "training AC IDs first 8; scored AC sorted by initial total length then ID, first 8",
                                "priority": "(current reduced total length, expanded prefix length, insertion order)",
                                "known_training_solutions_read": False},
              "common_target_ball": ball_report, "cases": []}
    official_lines = []
    training_lines = []
    for cohort, cases in (("training", train_cases), ("scored", formal_cases)):
        for challenge in cases:
            start = tuple(tuple(r) for r in challenge["initial_relators"])
            row = {"cohort": cohort, "challenge_id": challenge["challenge_id"],
                   "initial_relators": challenge["initial_relators"],
                   "initial_total_length": total_length(start), "arms": {}}
            for arm in ("primitive", "macro"):
                answer = search(start, ball, arm, args.budget, args.length_cap)
                if answer["status"] == "solved":
                    manifest = training if cohort == "training" else official
                    answer["official_verification"] = verify(
                        challenge, answer["moves"], "ac-r2-v1", manifest["limits"])
                    assert answer["official_verification"]["ok"] is True
                row["arms"][arm] = answer
            solved = [(answer["expanded_move_length"], arm, answer["moves"])
                      for arm, answer in row["arms"].items() if answer["status"] == "solved"]
            if solved:
                _, best_arm, moves = min(solved)
                row["selected_arm"] = best_arm
                line = challenge["challenge_id"] + ": " + json.dumps(moves)
                if cohort == "training":
                    training_lines.append(line)
                else:
                    official_lines.append(line)
                    stable_id = challenge["challenge_id"].replace("ac-", "sac-", 1)
                    official_lines.append(stable_id + ": " + json.dumps(moves + [16, 15]))
            report["cases"].append(row)
            print(challenge["challenge_id"],
                  {a: (r["status"], r["expanded_move_length"], r["primitive_evaluations"])
                   for a, r in row["arms"].items()}, flush=True)
    if training_lines:
        train_path = out / "training_submission.txt"
        train_path.write_text("\n".join(training_lines) + "\n", encoding="utf-8")
        report["training_selected_verified"] = official_verify(
            root, training_file, train_path, out / "training_verdict.json")
    if official_lines:
        official_path = out / "submission.txt"
        official_path.write_text("\n".join(official_lines) + "\n", encoding="utf-8")
        report["scored_selected_verified"] = official_verify(
            root, official_file, official_path, out / "official_verdict.json")
    report["limitations"] = ["heuristic bounded search, not a global shortest-path certificate",
                              "easy-biased fixed scored sample, not representative benchmark",
                              "no leaderboard comparison or platform upload",
                              "macro steps count at their full primitive expansion cost"]
    report["summary"] = {}
    for cohort in ("training", "scored"):
        rows = [r for r in report["cases"] if r["cohort"] == cohort]
        report["summary"][cohort] = {
            arm: {"solved": sum(r["arms"][arm]["status"] == "solved" for r in rows),
                  "cases": len(rows),
                  "primitive_evaluations": sum(r["arms"][arm]["primitive_evaluations"] for r in rows),
                  "expanded_solution_lengths": {
                      r["challenge_id"]: r["arms"][arm]["expanded_move_length"]
                      for r in rows if r["arms"][arm]["status"] == "solved"}}
            for arm in ("primitive", "macro")}
    (out / "results.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
