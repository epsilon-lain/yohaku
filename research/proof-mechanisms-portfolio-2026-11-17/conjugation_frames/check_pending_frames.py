#!/usr/bin/env python3
"""Versioned compatible-pending-frame extension; v1 evidence stays intact.

Shares v1's pinned official loader and cumulative apply ledger/caps.  Commands:
synthetic, development.  Access is restricted to old20 and old07445.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from pathlib import Path
import json
import traceback

import check_frames as base
from frame_rules import compile_frame
from pending_frame_rules import RULE_VERSION, pending_frame_candidates

HERE = Path(__file__).resolve().parent
CONFIG = dict(base.CONFIG, revision=2, rule_version=RULE_VERSION,
              enumeration="all rank-fixed I/M/C intervals whose each M has syntactically equal reduced pending target/donor words; require nonempty shared frame carried through M; strict primitive shortening",
              provenance="interleaved opening / partial closing extension prompted by peer symbolic_rules message identifying sym-dev-010/011 as common-frame special cases; no new8 access")


class Runtime(base.Runtime):
    @contextmanager
    def attempt(self, command):
        record = {"command": "v2-" + command, "started": base.now(),
                  "script_sha256": base.sha(Path(__file__).read_bytes()),
                  "core_script_sha256": base.sha((HERE / "check_frames.py").read_bytes()),
                  "rule_sha256": base.sha((HERE / "pending_frame_rules.py").read_bytes()),
                  "config_sha256": base.digest(CONFIG), "before": dict(self.counts)}
        self.ledger["attempts"].append(record)
        self.save()
        try:
            yield
            record["status"] = "completed"
        except BaseException as exc:
            record.update(status="failed", exception=type(exc).__name__, detail=str(exc),
                          traceback=traceback.format_exc())
            raise
        finally:
            record["finished"] = base.now()
            record["after"] = dict(self.counts)
            record["consumed"] = dict(self.counts - Counter(record["before"]))
            self.save()


def synthetic(rt):
    path = HERE / "checks-v2.json"
    if path.exists():
        raise RuntimeError("preserve/version completed v2 checks instead of overwriting")
    before = Counter(rt.counts)
    rows = []
    # Independent parameter checks of interleaved frame acquisition, followed
    # by multiplication and partial closing, not just a contiguous v1 pair.
    for rank in range(2, 9):
        initial = tuple((slot + 1, (slot + 1) % rank + 1, -(slot + 1))
                        for slot in range(rank))
        for letter in (1, -2):
            old = (rt.conj[rank - 1, letter], rt.inv[rank - 1],
                   rt.conj[0, letter], rt.mul[0, rank - 1, False],
                   rt.conj[0, -letter])
            expected = (rt.inv[rank - 1], rt.mul[0, rank - 1, False],
                        rt.conj[rank - 1, letter])
            result, states, _ = rt.pair(initial, old, expected,
                                        f"synthetic-pending-r{rank}-letter{letter}")
            candidates = list(pending_frame_candidates(old, states, rt.stable.MOVE_TABLE))
            assert any(row["start"] == 0 and row["end"] == 5 and
                       row["route"] == expected for row in candidates)
            result["recognized_candidates"] = len(candidates)
            rows.append(result)

    initial = ((1, -2), (-2,))
    old = (10, 1, 6, 2, 7, 11, 16, 15)
    new = (1, 2, 16, 15)
    complete, old_states, new_states = rt.pair(initial, old, new,
                                               "synthetic-interleaved-frame-complete", ())
    candidates = list(pending_frame_candidates(old, old_states, rt.stable.MOVE_TABLE))
    assert any(row["start"] == 0 and row["end"] == 6 and
               row["route"] == (1, 2) for row in candidates)
    complete["old_states"] = old_states
    complete["new_states"] = new_states

    # The single-slot counterexample must not pass the equality guard.
    initial = ((1,), (2,))
    wrong = (6, 2, 7)
    states = rt.replay(initial, wrong, "verification", "v2_guard_manual")
    assert not list(pending_frame_candidates(wrong, states, rt.stable.MOVE_TABLE))
    result = {"status": "passed", "created": base.now(), "matrix_case_count": len(rows),
              "matrix": rows, "complete_stable_certificate": complete,
              "single_slot_counterexample_rejected_by_guard": True,
              "counter_delta": dict(rt.counts - before), "counters_at_finish": dict(rt.counts)}
    base.dump(path, result)
    print(json.dumps({"v2_synthetic_status": "passed", "matrix_cases": len(rows),
                      "complete_old": complete["old"], "complete_new": complete["new"],
                      "counter_delta": result["counter_delta"]}))


def optimize(rt, case, original, ident):
    before = Counter(rt.counts)
    original_v = rt.verify(case, original, "v2_original_verify")
    assert original_v["ok"]
    states = rt.replay(case["initial_relators"], original, "search", "v2_trace")
    assert states[-1] == tuple(tuple(w) for w in case["target_relators"])
    original_states = states
    moves = tuple(original)
    attempts, accepted = [], []
    for iteration in range(CONFIG["maximum_accepted_rewrites"]):
        best = None
        for row in pending_frame_candidates(moves, states, rt.stable.MOVE_TABLE):
            a, b, route = row["start"], row["end"], row["route"]
            local = rt.replay(states[a], route, "search", "v2_candidate")
            assert local[-1] == states[b], (ident, row)
            proposed = moves[:a] + route + moves[b:]
            full_states = states[:a + 1] + local[1:] + states[b + 1:]
            value = base.metrics(full_states, proposed)
            feasible = (value["length"] <= base.LIMITS["max_path_length"] and
                        value["work"] <= base.LIMITS["max_work"] and
                        value["peak_total_relator_length"] <= base.LIMITS["max_total_relator_length"])
            attempts.append(dict(row, iteration=iteration, endpoint_exact=True,
                                 resource_feasible=feasible, full_metrics=value))
            key = (value["length"], value["work"], value["peak_total_relator_length"], a, b, proposed)
            if feasible and (best is None or key < best[0]):
                best = (key, row, proposed, full_states)
        if best is None:
            break
        _, row, moves, states = best
        verdict = rt.verify(case, moves, "v2_rewrite_verify")
        assert verdict["ok"]
        accepted.append(dict(row, full_official_verdict=verdict))
    final_v = rt.verify(case, moves, "v2_final_verify")
    assert final_v["ok"]
    before_m, after_m = base.metrics(original_states, original), base.metrics(states, moves)
    for value, verdict in ((before_m, original_v), (after_m, final_v)):
        assert all(value[key] == verdict[key] for key in ("length", "work", "peak_total_relator_length"))
    return {"source_id": ident, "challenge_id": case["challenge_id"],
            "initial_relators": case["initial_relators"], "target_relators": case["target_relators"],
            "instance_hash": case.get("instance_hash"), "original_moves": original, "final_moves": moves,
            "original_states": original_states, "final_states": states,
            "original_metrics": before_m, "final_metrics": after_m,
            "original_official_verdict": original_v, "final_official_verdict": final_v,
            "candidate_attempts": attempts, "accepted_rewrites": accepted,
            "counter_delta": dict(rt.counts - before)}


def development(rt):
    assert base.load(HERE / "checks-v2.json")["status"] == "passed"
    path = HERE / "results-v2.json"
    if path.exists():
        raise RuntimeError("preserve/version completed v2 results instead of overwriting")
    before = Counter(rt.counts)
    rows = []
    for case, moves, ident in base.records(rt):
        row = optimize(rt, case, moves, ident)
        rows.append(row)
        print(json.dumps({"id": ident, "before": row["original_metrics"]["length"],
                          "after": row["final_metrics"]["length"],
                          "candidates": len(row["candidate_attempts"])}), flush=True)
    result = {"status": "completed", "created": base.now(), "version": RULE_VERSION,
              "scope": CONFIG["scope"], "new8_test_actions_accessed": False,
              "old_v1_evaluation_actions_accessed": False, "case_count": len(rows), "cases": rows,
              "summary": {"original_total_length": sum(row["original_metrics"]["length"] for row in rows),
                          "final_total_length": sum(row["final_metrics"]["length"] for row in rows),
                          "candidate_count": sum(len(row["candidate_attempts"]) for row in rows),
                          "accepted_rewrites": sum(len(row["accepted_rewrites"]) for row in rows),
                          "improved_cases": sum(len(row["final_moves"]) < len(row["original_moves"]) for row in rows)},
              "counter_delta": dict(rt.counts - before), "counters_at_finish": dict(rt.counts)}
    base.dump(path, result)
    base.dump(HERE / "review-input-v2.json", {"scope": CONFIG["scope"], "rule_version": RULE_VERSION,
         "cases": [{key: row[key] for key in ("source_id", "challenge_id", "initial_relators",
                    "target_relators", "original_moves", "final_moves", "original_metrics", "final_metrics")}
                   for row in rows]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("synthetic", "development"))
    parser.add_argument("--official-root", type=Path, default=HERE.parent.parent / "ac_official")
    args = parser.parse_args()
    freeze = {"script_sha256": base.sha(Path(__file__).read_bytes()),
              "core_script_sha256": base.sha((HERE / "check_frames.py").read_bytes()),
              "rule_sha256": base.sha((HERE / "pending_frame_rules.py").read_bytes()),
              "v1_rule_sha256": base.sha((HERE / "frame_rules.py").read_bytes()),
              "config": CONFIG, "config_sha256": base.digest(CONFIG),
              "protocol_sha256": base.sha((HERE.parent / "PROTOCOL.json").read_bytes())}
    path = HERE / "FREEZE-v2.json"
    if path.exists():
        assert all(base.load(path)[key] == value for key, value in freeze.items())
    else:
        base.dump(path, dict(freeze, created=base.now(), access="only old20 and old07445; no new8"))
    rt = Runtime(args.official_root.resolve())
    with rt.attempt(args.command):
        synthetic(rt) if args.command == "synthetic" else development(rt)


if __name__ == "__main__":
    main()
