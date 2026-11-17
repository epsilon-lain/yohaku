#!/usr/bin/env python3
"""Pinned common-frame checks and old-development-only certificate scan.

Standard library only.  Every official apply, also failed calls and verify
internals, is counted in the cumulative attempt ledger.  No new test moves
are indexed.  Commands: synthetic, development.
"""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import traceback
import types

sys.dont_write_bytecode = True
from frame_rules import (RULE_VERSION, compile_frame, frame_candidates,
                         frame_intervals, inverse, reduce_word)

HERE = Path(__file__).resolve().parent
PIN = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
EXPECTED = {"canon": "93175152acd876566ff60bbfaf7cd90cd8cd2fa9",
            "core": "0a5da5fe6e3e42c96877734dad46b155a69c02b2",
            "stable_core": "af48e32f766dbcd0cad0becd8c1c4edb4358efac"}
LIMITS = {"max_path_length": 100000, "max_total_relator_length": 10000,
          "max_work": 5000000}
CONFIG = {"rule_version": RULE_VERSION, "revision": 1,
          "search_official_apply_cap_including_failures_retries": 250000,
          "verification_official_apply_cap_including_failures_retries": 5000,
          "scope": "old20 development original certificates plus old sac-07445 only",
          "maximum_accepted_rewrites": 3,
          "enumeration": "all pure-C intervals with common nonempty reduced word; pairs separated by nonempty I/M-only segment at fixed rank; strict primitive shortening",
          "choice": "full length, full work including initial, full peak, start, end, full move list",
          "limits": LIMITS}


def now():
    return datetime.now(timezone.utc).isoformat()


def sha(data):
    return hashlib.sha256(data).hexdigest()


def digest(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def dump(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def total(state):
    return sum(map(len, state))


def metrics(states, moves):
    lengths = list(map(total, states))
    return {"length": len(moves), "work": sum(lengths),
            "peak_total_relator_length": max(lengths),
            "state_total_lengths_including_initial": lengths}


def challenge(initial, target, ident):
    return {"challenge_id": ident, "move_spec_version": "sac-r8-v1",
            "initial_relators": initial, "target_relators": target}


class Runtime:
    def __init__(self, root):
        self.root = root
        self.protocol = load(HERE.parent / "PROTOCOL.json")
        assert self.protocol["official_commit"] == PIN
        lock = load(HERE.parent.parent / "proof_reconstruction_round2_20261117/OFFICIAL-SOURCE-LOCK.json")
        assert lock["commit"] == PIN and len(lock["files"]) == 30
        self.checked = {}
        for entry in lock["files"]:
            data = (root / entry["path"]).read_bytes()
            assert blob(data) == entry["git_blob"] and sha(data) == entry["sha256"], entry["path"]
            self.checked[entry["path"]] = data
        self.ledger_path = HERE / "attempt-ledger.json"
        self.ledger = load(self.ledger_path, {"attempts": [], "counters": {}})
        self.counts = Counter(self.ledger["counters"])
        self.phase = "unassigned"
        self.kind = "verification"
        pkgname = "_pinned_portfolio_frames"
        package = types.ModuleType(pkgname)
        package.__path__ = [str(root / "competition/tools/verifier")]
        sys.modules[pkgname] = package
        for name, expected in EXPECTED.items():
            path = "competition/tools/verifier/" + name + ".py"
            data = self.checked[path]
            assert blob(data) == expected
            module = types.ModuleType(pkgname + "." + name)
            module.__file__ = str(root / path)
            module.__package__ = pkgname
            setattr(package, name, module)
            sys.modules[module.__name__] = module
            exec(compile(data, module.__file__, "exec"), module.__dict__)
        self.stable = package.stable_core
        original_apply = self.stable.apply_move

        def counted_apply(state, move):
            key = self.kind + "_official_apply"
            cap = CONFIG[key.replace("_official_apply", "_official_apply_cap_including_failures_retries")]
            if self.counts[key] >= cap:
                raise RuntimeError("cumulative " + key + " cap reached")
            self.counts[key] += 1
            self.counts[self.phase + "_apply"] += 1
            return original_apply(state, move)

        self.stable.apply_move = counted_apply
        self.inv = {row["relator"]: row["id"] for row in self.stable.MOVE_TABLE
                    if row["category"] == "inversion"}
        self.mul = {(row["relator"], row["other"], row["invert_other"]): row["id"]
                    for row in self.stable.MOVE_TABLE if row["category"] == "multiplication"}
        self.conj = {(row["relator"], row["conjugator"]): row["id"]
                     for row in self.stable.MOVE_TABLE if row["category"] == "conjugation"}

    def save(self):
        self.ledger["counters"] = dict(self.counts)
        dump(self.ledger_path, self.ledger)

    @contextmanager
    def attempt(self, command):
        record = {"command": command, "started": now(),
                  "script_sha256": sha(Path(__file__).read_bytes()),
                  "rule_sha256": sha((HERE / "frame_rules.py").read_bytes()),
                  "config_sha256": digest(CONFIG), "before": dict(self.counts)}
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
            record["finished"] = now()
            record["after"] = dict(self.counts)
            record["consumed"] = dict(self.counts - Counter(record["before"]))
            self.save()

    @contextmanager
    def using(self, kind, phase):
        previous = self.kind, self.phase
        self.kind, self.phase = kind, phase
        try:
            yield
        finally:
            self.kind, self.phase = previous

    def replay(self, initial, moves, kind, phase):
        with self.using(kind, phase):
            states = [tuple(tuple(word) for word in initial)]
            for move in moves:
                result, reason = self.stable.apply_move(states[-1], move)
                if reason:
                    raise ValueError((move, reason))
                states.append(result)
            return states

    def verify(self, case, moves, phase):
        with self.using("verification", phase):
            self.counts["official_verify_calls"] += 1
            return self.stable.verify(case, list(moves), "sac-r8-v1", LIMITS)

    def pair(self, initial, old, new, name, target=None):
        old_states = self.replay(initial, old, "verification", "synthetic_manual")
        new_states = self.replay(initial, new, "verification", "synthetic_manual")
        assert old_states[-1] == new_states[-1], name
        if target is not None:
            assert old_states[-1] == target
        case = challenge(initial, old_states[-1], name)
        old_v = self.verify(case, old, "synthetic_verify")
        new_v = self.verify(case, new, "synthetic_verify")
        assert old_v["ok"] and new_v["ok"], (name, old_v, new_v)
        result = {"name": name, "initial": initial, "target": old_states[-1],
                  "old_moves": old, "new_moves": new,
                  "old": metrics(old_states, old), "new": metrics(new_states, new),
                  "old_official": old_v, "new_official": new_v}
        for key in ("length", "work", "peak_total_relator_length"):
            assert result["old"][key] == old_v[key]
            assert result["new"][key] == new_v[key]
        return result, old_states, new_states


def synthetic(rt):
    if (HERE / "checks.json").exists():
        raise RuntimeError("checks.json exists; version any intentional rerun instead of overwriting")
    rows = []
    for rank in range(2, 9):
        initial = tuple((slot + 1, (slot + 1) % rank + 1, -(slot + 1))
                        for slot in range(rank))
        if rank == 3:
            initial = ((),) + initial[1:]
        middle = (rt.inv[0], rt.mul[0, rank - 1, False], rt.inv[rank - 1],
                  rt.mul[rank - 1, 0, True])
        for index, (h, g) in enumerate((((1,), (-1,)),
                                       ((1, 2), (-1,)),
                                       ((1, 2), (2, -1)))):
            old = (compile_frame(rank, h, rt.stable.MOVE_TABLE) + middle +
                   compile_frame(rank, g, rt.stable.MOVE_TABLE))
            new = middle + compile_frame(rank, reduce_word(g + h), rt.stable.MOVE_TABLE)
            result, states, _ = rt.pair(initial, old, new, f"synthetic-frame-r{rank}-{index}")
            candidates = list(frame_candidates(old, states, rt.stable.MOVE_TABLE))
            assert any(row["start"] == 0 and row["end"] == len(old) and
                       row["route"] == new for row in candidates)
            result["recognized_candidates"] = len(candidates)
            rows.append(result)

    # A complete Stable certificate with a genuine I/M proof segment.
    initial = ((1, 2, -1), (1, -2))
    h = (1, 2)
    middle = (2, 1, 4)
    old = (compile_frame(2, h, rt.stable.MOVE_TABLE) + middle +
           compile_frame(2, inverse(h), rt.stable.MOVE_TABLE) + (16, 15))
    new = middle + (16, 15)
    complete, old_states, new_states = rt.pair(initial, old, new,
                                               "synthetic-complete-stable", ())
    candidates = list(frame_candidates(old, old_states, rt.stable.MOVE_TABLE))
    assert any(row["start"] == 0 and row["end"] == 11 and
               row["route"] == middle for row in candidates)
    complete["old_states"] = old_states
    complete["new_states"] = new_states

    # Common-frame hypothesis cannot be dropped for a single slot.
    initial = ((1,), (2,))
    wrong_old = (6, 2, 7)
    wrong_new = (2,)
    a = rt.replay(initial, wrong_old, "verification", "synthetic_counterexample")
    b = rt.replay(initial, wrong_new, "verification", "synthetic_counterexample")
    assert a[-1] == ((2, 1), (2,)) and b[-1] == ((1, 2), (2,))
    single = {"initial": initial, "old_moves": wrong_old, "proposed_moves": wrong_new,
              "old_endpoint": a[-1], "proposed_endpoint": b[-1]}

    # A conjugation in P is not covered by I/M equivariance.
    old = compile_frame(2, (1,), rt.stable.MOVE_TABLE) + (8,) + compile_frame(2, (-1,), rt.stable.MOVE_TABLE)
    a = rt.replay(initial, old, "verification", "synthetic_counterexample")
    b = rt.replay(initial, (8,), "verification", "synthetic_counterexample")
    assert a[-1] != b[-1]
    conjugation_middle = {"initial": initial, "old_moves": old,
                          "proposed_moves": [8], "old_endpoint": a[-1],
                          "proposed_endpoint": b[-1]}

    # Stabilization does not commute with extending the frame to the fresh slot.
    a = rt.replay(initial, compile_frame(2, (1,), rt.stable.MOVE_TABLE) + (14,),
                  "verification", "synthetic_counterexample")
    b = rt.replay(initial, (14,) + compile_frame(3, (1,), rt.stable.MOVE_TABLE),
                  "verification", "synthetic_counterexample")
    assert a[-1] != b[-1]
    stabilization = {"initial": initial, "frame_then_Z_endpoint": a[-1],
                     "Z_then_extended_frame_endpoint": b[-1]}

    # Destabilization can lose applicability under common conjugation.
    a = rt.replay(initial, (15,), "verification", "synthetic_counterexample")
    framed = rt.replay(initial, compile_frame(2, (2,), rt.stable.MOVE_TABLE),
                       "verification", "synthetic_counterexample")[-1]
    with rt.using("verification", "synthetic_counterexample"):
        failed, reason = rt.stable.apply_move(framed, 15)
    assert failed is None and reason == "destabilize_precondition"
    destabilization = {"initial": initial, "D0_endpoint": a[-1],
                       "common_Cy_state": framed, "D0_after_frame_reason": reason}

    # Fewer primitives and the same endpoint do not imply resource feasibility.
    initial = ((-1,) + (2,) * 5000 + (1,), (-1,) + (2,) * 2500 + (1,))
    old = compile_frame(2, (1,), rt.stable.MOVE_TABLE) + (2, 3) + compile_frame(2, (-1,), rt.stable.MOVE_TABLE)
    new = (2, 3)
    a = rt.replay(initial, old, "verification", "synthetic_resource_manual")
    b = rt.replay(initial, new, "verification", "synthetic_resource_manual")
    assert a[-1] == b[-1] == initial
    case = challenge(initial, initial, "synthetic-frame-resource-guard")
    old_v = rt.verify(case, old, "synthetic_resource_verify")
    new_v = rt.verify(case, new, "synthetic_resource_verify")
    assert old_v["ok"] and new_v["code"] == "E_LENGTH_LIMIT"
    assert metrics(a, old)["peak_total_relator_length"] == 10000
    assert metrics(b, new)["peak_total_relator_length"] == 10004
    resource = {"initial_definition": "(x^-1 y^5000 x, x^-1 y^2500 x)",
                "initial_sha256": digest(initial), "old_moves": old, "proposed_moves": new,
                "old": metrics(a, old), "proposed": metrics(b, new),
                "old_official": old_v, "proposed_official": new_v}

    result = {"status": "passed", "created": now(), "rank_matrix_case_count": len(rows),
              "rank_matrix": rows, "complete_stable_certificate": complete,
              "counterexamples": {"single_slot": single, "conjugation_middle": conjugation_middle,
                                   "stabilization": stabilization, "destabilization": destabilization,
                                   "resource": resource},
              "counters_at_finish": dict(rt.counts)}
    dump(HERE / "checks.json", result)
    print(json.dumps({"synthetic_status": "passed", "matrix_cases": len(rows),
                      "complete_old": complete["old"], "complete_new": complete["new"],
                      "counts": dict(rt.counts)}))


def records(rt):
    ids = rt.protocol["known_development_training_ids"]
    assert len(ids) == 20
    allow = set(ids)
    source = json.loads(rt.checked["competition/examples/stable_training_424.json"])
    # Membership is tested before any move-array indexing; no new8/excluded arrays accessed.
    selected = {row["training_id"]: row for row in source["instances"]
                if row["training_id"] in allow}
    assert set(selected) == allow
    training_manifest = json.loads(rt.checked["competition/examples/training_manifest.json"])
    manifests = {row["challenge_id"]: row for row in training_manifest["challenges"]}
    result = []
    for ident in ids:
        row = selected[ident]
        official_id = ident.replace("ms-train-", "sac-train-", 1)
        case = manifests[official_id]
        for key in ("initial_relators", "target_relators", "move_spec_version"):
            assert case[key] == row[key]
        result.append((case, row["moves"], ident))
    manifest = json.loads(rt.checked["competition/tools/verifier/data/manifest.json"])
    incumbent = rt.protocol["old_scored_incumbent"]
    case = next(row for row in manifest["challenges"] if row["challenge_id"] == incumbent["id"])
    result.append((case, incumbent["moves"], incumbent["id"]))
    return result


def optimize(rt, case, original, source_id):
    before = Counter(rt.counts)
    original_v = rt.verify(case, original, "development_original_verify")
    assert original_v["ok"], (case["challenge_id"], original_v)
    states = rt.replay(case["initial_relators"], original, "search", "development_trace")
    assert states[-1] == tuple(tuple(w) for w in case["target_relators"])
    moves = tuple(original)
    original_states = states
    accepted, attempts = [], []
    frame_count = 0
    for iteration in range(CONFIG["maximum_accepted_rewrites"]):
        frame_count += len(frame_intervals(moves, states, rt.stable.MOVE_TABLE))
        best = None
        for row in frame_candidates(moves, states, rt.stable.MOVE_TABLE):
            a, b, route = row["start"], row["end"], row["route"]
            local = rt.replay(states[a], route, "search", "development_candidate")
            exact = local[-1] == states[b]
            assert exact, (source_id, row, local[-1], states[b])
            proposed = moves[:a] + route + moves[b:]
            full_states = states[:a + 1] + local[1:] + states[b + 1:]
            value = metrics(full_states, proposed)
            feasible = (value["length"] <= LIMITS["max_path_length"] and
                        value["work"] <= LIMITS["max_work"] and
                        value["peak_total_relator_length"] <= LIMITS["max_total_relator_length"])
            attempts.append(dict(row, iteration=iteration, endpoint_exact=exact,
                                 resource_feasible=feasible, full_metrics=value))
            if feasible:
                key = (value["length"], value["work"], value["peak_total_relator_length"],
                       a, b, proposed)
                if best is None or key < best[0]:
                    best = (key, row, proposed, full_states)
        if best is None:
            break
        _, row, moves, states = best
        verdict = rt.verify(case, moves, "development_rewrite_verify")
        assert verdict["ok"], verdict
        accepted.append(dict(row, full_official_verdict=verdict))
    final_v = rt.verify(case, moves, "development_final_verify")
    assert final_v["ok"]
    original_m, final_m = metrics(original_states, original), metrics(states, moves)
    for value, verdict in ((original_m, original_v), (final_m, final_v)):
        for key in ("length", "work", "peak_total_relator_length"):
            assert value[key] == verdict[key]
    return {"source_id": source_id, "challenge_id": case["challenge_id"],
            "initial_relators": case["initial_relators"], "target_relators": case["target_relators"],
            "instance_hash": case.get("instance_hash"),
            "original_moves": original, "final_moves": moves,
            "original_states": original_states, "final_states": states,
            "original_metrics": original_m, "final_metrics": final_m,
            "original_official_verdict": original_v, "final_official_verdict": final_v,
            "common_frame_intervals_seen": frame_count, "candidate_attempts": attempts,
            "accepted_rewrites": accepted, "counter_delta": dict(rt.counts - before)}


def development(rt):
    assert load(HERE / "checks.json")["status"] == "passed"
    if (HERE / "results.json").exists():
        raise RuntimeError("results.json exists; preserve and version any rerun")
    before = Counter(rt.counts)
    output = []
    for case, moves, ident in records(rt):
        row = optimize(rt, case, moves, ident)
        output.append(row)
        print(json.dumps({"case": ident, "before": row["original_metrics"]["length"],
                          "after": row["final_metrics"]["length"],
                          "frames": row["common_frame_intervals_seen"],
                          "candidates": len(row["candidate_attempts"])}), flush=True)
    result = {"status": "completed", "created": now(), "scope": CONFIG["scope"],
              "new8_test_actions_accessed": False, "old_v1_evaluation_actions_accessed": False,
              "case_count": len(output), "cases": output,
              "summary": {"original_total_length": sum(row["original_metrics"]["length"] for row in output),
                          "final_total_length": sum(row["final_metrics"]["length"] for row in output),
                          "common_frame_intervals": sum(row["common_frame_intervals_seen"] for row in output),
                          "candidate_count": sum(len(row["candidate_attempts"]) for row in output),
                          "accepted_rewrites": sum(len(row["accepted_rewrites"]) for row in output)},
              "counter_delta": dict(rt.counts - before), "counters_at_finish": dict(rt.counts)}
    dump(HERE / "results.json", result)
    dump(HERE / "review-input.json", {"scope": CONFIG["scope"], "rule_version": RULE_VERSION,
         "cases": [{key: row[key] for key in ("source_id", "challenge_id", "initial_relators",
                    "target_relators", "original_moves", "final_moves", "original_metrics", "final_metrics")}
                   for row in output]})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("synthetic", "development"))
    parser.add_argument("--official-root", type=Path, default=HERE.parent.parent / "ac_official")
    args = parser.parse_args()
    freeze_path = HERE / "FREEZE.json"
    freeze = {"script_sha256": sha(Path(__file__).read_bytes()),
              "rule_sha256": sha((HERE / "frame_rules.py").read_bytes()),
              "config": CONFIG, "config_sha256": digest(CONFIG),
              "protocol_sha256": sha((HERE.parent / "PROTOCOL.json").read_bytes())}
    if freeze_path.exists():
        saved = load(freeze_path)
        assert all(saved[key] == value for key, value in freeze.items()), "frozen execution code/config changed"
    else:
        dump(freeze_path, dict(freeze, created=now(), access="no new8 test actions needed or allowed"))
    rt = Runtime(args.official_root.resolve())
    with rt.attempt(args.command):
        if args.command == "synthetic":
            synthetic(rt)
        else:
            development(rt)


if __name__ == "__main__":
    main()
