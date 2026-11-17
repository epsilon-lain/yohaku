#!/usr/bin/env python3
"""Pinned, bounded, certificate postprocessing experiment; standard library only.

Commands (in this order): selfcheck, development, freeze, test, report.
New public-test move arrays are not accessed before FREEZE.json is written.
No external solver, network, platform submission, or native-host session is used.
"""

import argparse
from collections import Counter, defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import itertools
import json
from pathlib import Path
import sys
import time
import traceback
import types

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PIN = "a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e"
BLOBS = {
    "competition/examples/stable_training_424.json": "22428166cb348d41bbc92e24ab9e2a49e1ebd235",
    "competition/tools/verifier/core.py": "0a5da5fe6e3e42c96877734dad46b155a69c02b2",
    "competition/tools/verifier/stable_core.py": "af48e32f766dbcd0cad0becd8c1c4edb4358efac",
    "competition/tools/verifier/canon.py": "93175152acd876566ff60bbfaf7cd90cd8cd2fa9",
    "competition/tools/verifier/data/manifest.json": "accdb626ee08a06beea3f88dc7f351514c99eb27",
    "competition/examples/training_manifest.json": "3f2fba9fc7ca1c6136b33d0941d18adab40aa94f",
}
CONFIG = {
    "version": "proof-reconstruction-cloud-r2-v1",
    "implementation_revision": 2,
    "selection_salt": "proof_reconstruction_cloud_r2_v1",
    "search_apply_cap_per_arm_case": 50000,
    "search_wall_seconds_per_arm_case": 15,
    "total_armcase_search_apply_cap": 2100000,
    "total_verification_apply_cap_including_diagnostics": 30000,
    "application_verification_apply_cap_including_diagnostics": 25000,
    "external_verification_apply_reservations": {"theory": 2000, "root_independent_recheck": 3000},
    "maximum_accepted_rewrites": 3,
    "max_h_length": 2,
    "test_count": 16,
    "maximum_test_original_length": 20,
    "limits": {"max_path_length": 100000,
               "max_total_relator_length": 10000, "max_work": 5000000},
    "official_max_rank": 8,
    "candidate_order": "start index; loops; primitive move id; left(target,donor,sign); conjugated_donor(h length, h lexical, target,donor,sign)",
    "choice_key": "full resulting primitive length, full work, full peak, start, end-exclusive, full expanded move list",
    "primitive_prefilter": "none: all 257 ids attempted where a one-step strict shortening is possible; official inapplicability counted",
    "macro_expansion": "every candidate primitive is individually passed to official apply_move; no prefix memoization or uncharged algebraic endpoint",
    "scope": "fixed known-certificate compression, not a from-scratch solver or original-v1-solver comparison",
}


def now():
    return datetime.now(timezone.utc).isoformat()


def dump(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def sha(data):
    return hashlib.sha256(data).hexdigest()


def json_sha(obj):
    return sha(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def state_json(state):
    return [list(w) for w in state]


def word_inverse(w):
    return tuple(-a for a in reversed(w))


def independent_reduce(word):
    out = []
    for a in word:
        if out and out[-1] == -a:
            out.pop()
        else:
            out.append(a)
    return tuple(out)


class SearchStopped(Exception):
    pass


class VerificationStopped(Exception):
    pass


class Runtime:
    def __init__(self, source_root, output):
        self.source_root, self.output = source_root, output
        self.output.mkdir(parents=True, exist_ok=True)
        self.protocol_path = HERE.parent / "PROTOCOL.json"
        self.protocol = read(self.protocol_path)
        self.source_hashes = {}
        self.checked_bytes = {}
        # Every executable source is checked before import; JSON before loading.
        for rel, expected in BLOBS.items():
            data = (source_root / rel).read_bytes()
            actual = blob(data)
            if actual != expected:
                raise RuntimeError(f"pinned Git blob mismatch: {rel}: {actual}")
            self.source_hashes[rel] = {"git_blob": actual, "sha256": sha(data)}
            self.checked_bytes[rel] = data
        self.ledger_path = output / "attempt-ledger.json"
        self.ledger = read(self.ledger_path, {"attempts": [], "counters": {}, "armcase_consumption": {}})
        self.counters = Counter(self.ledger["counters"])
        self.phase = "unassigned"
        self.current = None
        self.deadline = None
        self.run_started = None
        self.failures = []
        self._load_official()
        self.inv = {r["relator"]: r["id"] for r in self.stable.MOVE_TABLE if r["category"] == "inversion"}
        self.mul = {(r["relator"], r["other"], r["invert_other"]): r["id"] for r in self.stable.MOVE_TABLE if r["category"] == "multiplication"}
        self.conj = {(r["relator"], r["conjugator"]): r["id"] for r in self.stable.MOVE_TABLE if r["category"] == "conjugation"}

    def _load_official(self):
        verifier = self.source_root / "competition/tools/verifier"
        pkgname = "_pinned_reconstruction_r2"
        pkg = types.ModuleType(pkgname)
        pkg.__path__ = [str(verifier)]
        sys.modules[pkgname] = pkg
        loaded = {}
        for name in ("canon", "core", "stable_core"):
            module_name = f"{pkgname}.{name}"
            module = types.ModuleType(module_name)
            module.__file__ = str(verifier / f"{name}.py")
            module.__package__ = pkgname
            sys.modules[module_name] = module
            setattr(pkg, name, module)
            source = self.checked_bytes[f"competition/tools/verifier/{name}.py"]
            exec(compile(source, module.__file__, "exec"), module.__dict__)
            loaded[name] = module
        self.stable = loaded["stable_core"]
        self.canon = loaded["canon"]
        self.original_apply = self.stable.apply_move

        def counted_apply(state, move):
            if self.phase.endswith("search"):
                self._check_search()
            self.counters[self.phase + "_apply"] += 1
            if self.current is not None:
                key = "verification_apply_calls" if self.phase.endswith("verification") else "search_apply_calls"
                self.current[key] += 1
            return self.original_apply(state, move)

        # Wrap stable.apply_move once. stable.verify resolves this same global.
        # core.apply_move is not wrapped or called by stable.apply_move.
        self.stable.apply_move = counted_apply
        assert self.stable.MAX_RANK == CONFIG["official_max_rank"]

    def _check_search(self):
        if self.current is not None:
            if self.current["search_apply_calls"] >= self.current["remaining_apply_budget"]:
                raise SearchStopped("official_apply_cap")
            if time.monotonic() >= self.deadline:
                raise SearchStopped("wall_time_cap")
        total = sum(v for k, v in self.counters.items() if k.endswith("search_apply"))
        if total >= CONFIG["total_armcase_search_apply_cap"]:
            raise SearchStopped("global_search_apply_cap_including_diagnostics_and_retries")

    def save_ledger(self):
        self.ledger["counters"] = dict(self.counters)
        dump(self.ledger_path, self.ledger)

    @contextmanager
    def attempt(self, command):
        entry = {"id": str(time.time_ns()), "command": command, "started": now(),
                 "script_sha256": sha(Path(__file__).read_bytes()),
                 "config_sha256": json_sha(CONFIG), "before_counters": dict(self.counters)}
        self.ledger["attempts"].append(entry)
        self.save_ledger()
        try:
            yield entry
            entry["status"] = "completed"
        except BaseException as exc:
            entry.update(status="failed", exception=type(exc).__name__, detail=str(exc), traceback=traceback.format_exc())
            raise
        finally:
            entry["finished"] = now()
            entry["after_counters"] = dict(self.counters)
            entry["consumed_counters"] = dict(self.counters - Counter(entry["before_counters"]))
            self.save_ledger()

    def verify(self, challenge, moves, phase):
        used = sum(v for k, v in self.counters.items() if k.endswith("verification_apply"))
        if used + len(moves) > CONFIG["application_verification_apply_cap_including_diagnostics"]:
            raise VerificationStopped("global verification apply cap (conservative full-path reservation)")
        previous = self.phase
        self.phase = phase + "_verification"
        self.counters[self.phase + "_calls"] += 1
        try:
            return self.stable.verify(challenge, list(moves), self.stable.MOVE_SPEC_VERSION, CONFIG["limits"])
        finally:
            self.phase = previous

    def training_metadata(self):
        # JSON decoding necessarily materializes the public file. Until freeze,
        # selection reads ONLY training_id and declared length, never move arrays.
        return json.loads((self.source_root / "competition/examples/stable_training_424.json").read_text())

    def provenance(self):
        return {
            "created": now(), "execution": "cloud auxiliary application study",
            "native_yohaku_session_connected": False, "native_team_started": False,
            "official_commit_asserted_by_fixed_protocol": PIN,
            "source_checkout_has_git_metadata": (self.source_root / ".git").exists(),
            "source_checks": self.source_hashes,
            "loader": "minimal types.ModuleType package: canon, core, stable_core; exec(compile(exact hash-checked bytes)) without verifier.__init__ or pyc loading",
            "API_accounting": "stable_core.apply_move wrapped once; verify internal apply calls use the same wrapper under a separate phase; core.apply_move is not wrapped, and is not called by stable_core.apply_move",
            "source_route": "preexisting cloud cache under ac_official; no source fetched and no host filesystem/session accessed",
            "permissions": "parent-directed, user-authorized fixed public certificate postprocessing; no platform/leaderboard access, no submission, no direct GitHub writes",
            "limits": CONFIG["limits"], "config": CONFIG,
            "source_access_boundary": "full public JSON may be decoded; excluded prior-evaluation move arrays are never indexed, printed, replayed, or analyzed; no structure_discovery_next_20261117 files opened",
        }


def challenge_for(record):
    source_id = record.get("training_id")
    official_id = source_id.replace("ms-train-", "sac-train-", 1) if source_id else record["challenge_id"]
    return {"challenge_id": official_id,
            "source_training_id": source_id,
            "move_spec_version": record["move_spec_version"],
            "initial_relators": record["initial_relators"],
            "target_relators": record["target_relators"]}


def h_words(rank):
    letters = tuple(a for g in range(1, rank + 1) for a in (g, -g))
    yield ()
    for length in range(1, CONFIG["max_h_length"] + 1):
        for w in itertools.product(letters, repeat=length):
            if all(w[j] != -w[j - 1] for j in range(1, length)):
                yield w


def left_compile(rt, i, j, sign):
    return (rt.inv[i], rt.mul[(i, j, sign == 1)], rt.inv[i])


def donor_compile(rt, i, j, sign, h=()):
    # For h=(a1,...,am): first C_a1^-1,...,C_am^-1, then donor,
    # then C_am,...,C_a1. Execution-order reversal is intentional.
    donor = (rt.inv[i], rt.mul[(i, j, sign == 1)],
             rt.inv[i], rt.mul[(i, j, sign == 1)])
    return tuple(rt.conj[(i, -a)] for a in h) + donor + tuple(rt.conj[(i, a)] for a in reversed(h))


def replacements(rt, rank, arm, maximum_length):
    if maximum_length >= 1:
        for move in range(rt.stable.NUM_MOVES):
            yield "primitive", (move,), {"move": move}
    if arm == "baseline" or rank < 2:
        return
    pairs = tuple((i, j, s) for i in range(rank) for j in range(rank) if j != i for s in (1, -1))
    if maximum_length >= 3:
        for i, j, sign in pairs:
            yield "left_multiplication", left_compile(rt, i, j, sign), {"target": i, "donor": j, "sign": sign}
    for h in h_words(rank):
        if 2 * len(h) + 4 > maximum_length:
            continue
        for i, j, sign in pairs:
            family = "donor_conjugation" if not h else "conjugated_donor"
            yield family, donor_compile(rt, i, j, sign, h), {"target": i, "donor": j, "sign": sign, "h": list(h)}


def replay(rt, challenge, moves):
    states = [tuple(tuple(w) for w in challenge["initial_relators"])]
    for move in moves:
        state, reason = rt.stable.apply_move(states[-1], move)
        if reason:
            raise RuntimeError(f"current certificate contains inapplicable move: {reason}")
        states.append(state)
    return states


def optimize(rt, challenge, input_moves, arm, group):
    case_id = challenge["challenge_id"]
    # Stable official challenge id and source training label are distinct.
    # Revision-1 consumption used ms-train labels, so retain exactly that key.
    budget_identity = challenge.get("source_training_id") or case_id
    key = group + ":" + budget_identity + ":" + arm
    prior = rt.ledger["armcase_consumption"].get(key, {"search_apply_calls": 0, "wall_seconds": 0.0})
    result = {
        "case_id": case_id, "group": group, "arm": arm,
        "source_training_id": challenge.get("source_training_id"), "budget_identity": budget_identity,
        "original_moves": list(input_moves), "original_length": len(input_moves),
        "script_sha256": sha(Path(__file__).read_bytes()), "config_sha256": json_sha(CONFIG),
        "search_apply_calls": 0, "verification_apply_calls": 0,
        "remaining_apply_budget": max(0, CONFIG["search_apply_cap_per_arm_case"] - prior["search_apply_calls"]),
        "remaining_wall_budget": max(0.0, CONFIG["search_wall_seconds_per_arm_case"] - prior["wall_seconds"]),
        "prior_attempt_consumption": prior, "accepted": [], "rounds": [],
        "verification_failures": [], "terminal_rank": len(challenge["target_relators"]),
        "limits": CONFIG["limits"], "cap_status": [],
    }
    rt.current = result
    rt.phase = group + "_search"
    started = time.monotonic()
    rt.deadline = started + result["remaining_wall_budget"]
    moves = list(input_moves)
    phase = group if group != "diagnostic" else "diagnostic"
    try:
        original = rt.verify(challenge, moves, phase)
        result["original_verdict"] = original
        if not original["ok"]:
            raise RuntimeError(f"original certificate rejected: {original}")
        final_verdict = original
        for iteration in range(CONFIG["maximum_accepted_rewrites"]):
            stats = {"iteration": iteration, "starting_length": len(moves),
                     "candidate_routes_started": 0, "candidate_routes_completed": 0,
                     "inapplicable": {}, "route_length_limit_rejections": 0,
                     "exact_endpoint_matches": 0, "resource_filtered_matches": 0,
                     "distinct_feasible_new_paths": 0, "exhaustive": True}
            result["rounds"].append(stats)
            candidates = {}
            try:
                rt._check_search()
                states = replay(rt, challenge, moves)
                lens = [sum(map(len, state)) for state in states]
                prefix_work = [0]
                for length in lens:
                    prefix_work.append(prefix_work[-1] + length)
                state_index = defaultdict(list)
                for index, state in enumerate(states):
                    state_index[state].append(index)

                def consider(start, endpoint, route, route_lens, family, parameters):
                    for end in state_index.get(endpoint, ()):
                        if end <= start or end - start <= len(route):
                            continue
                        stats["exact_endpoint_matches"] += 1
                        new_moves = tuple(moves[:start]) + tuple(route) + tuple(moves[end:])
                        work = prefix_work[-1] - (prefix_work[end + 1] - prefix_work[start + 1]) + sum(route_lens)
                        peak = max(lens[:start + 1] + route_lens + lens[end + 1:])
                        if (len(new_moves) > CONFIG["limits"]["max_path_length"]
                                or work > CONFIG["limits"]["max_work"]
                                or peak > CONFIG["limits"]["max_total_relator_length"]):
                            stats["resource_filtered_matches"] += 1
                            continue
                        choice_key = (len(new_moves), work, peak, start, end, new_moves)
                        item = {"start": start, "end_exclusive": end,
                                "removed_moves": moves[start:end], "replacement_moves": list(route),
                                "family": family, "parameters": parameters,
                                "predicted_length": len(new_moves), "predicted_work": work,
                                "predicted_peak": peak, "endpoint": state_json(endpoint),
                                "new_moves": list(new_moves)}
                        old = candidates.get(new_moves)
                        if old is None or choice_key < old[0]:
                            candidates[new_moves] = (choice_key, item)

                for start, state in enumerate(states[:-1]):
                    rt._check_search()
                    consider(start, state, (), [], "exact_state_loop", {})
                    maximum_length = len(moves) - start - 1
                    for family, route, parameters in replacements(rt, len(state), arm, maximum_length):
                        rt._check_search()
                        stats["candidate_routes_started"] += 1
                        endpoint, route_lens = state, []
                        for move in route:
                            endpoint, reason = rt.stable.apply_move(endpoint, move)
                            if reason is not None:
                                stats["inapplicable"][reason] = stats["inapplicable"].get(reason, 0) + 1
                                break
                            length = sum(map(len, endpoint))
                            route_lens.append(length)
                            if length > CONFIG["limits"]["max_total_relator_length"]:
                                stats["route_length_limit_rejections"] += 1
                                break
                        else:
                            stats["candidate_routes_completed"] += 1
                            consider(start, endpoint, route, route_lens, family, parameters)
            except SearchStopped as exc:
                stats["exhaustive"] = False
                stats["stop_reason"] = str(exc)
                result["cap_status"].append(str(exc))
            stats["distinct_feasible_new_paths"] = len(candidates)
            accepted = None
            for _, candidate in sorted(candidates.values(), key=lambda entry: entry[0]):
                verdict = rt.verify(challenge, candidate["new_moves"], phase)
                if not verdict["ok"]:
                    result["verification_failures"].append({"iteration": iteration, "candidate": candidate, "verdict": verdict})
                    continue
                assert verdict["length"] == candidate["predicted_length"]
                assert verdict["work"] == candidate["predicted_work"]
                assert verdict["peak_total_relator_length"] == candidate["predicted_peak"]
                assert verdict["length"] < len(moves)
                candidate["official_verdict"] = verdict
                candidate["selection_scope"] = "globally best feasible enumerated candidate; " + ("full configured library exhausted" if stats["exhaustive"] else "search truncated by fixed cap")
                accepted = candidate
                break
            if accepted is None:
                result["stop_reason"] = "no_strict_shortening" if stats["exhaustive"] else "cap_without_accepted_candidate"
                break
            result["accepted"].append(accepted)
            moves, final_verdict = accepted["new_moves"], accepted["official_verdict"]
            if not stats["exhaustive"]:
                result["stop_reason"] = "cap_after_acceptance"
                break
        else:
            result["stop_reason"] = "maximum_three_acceptances"
        result["final_moves"] = moves
        result["final_verdict"] = rt.verify(challenge, moves, phase)
        assert result["final_verdict"]["ok"]
        result["final_length"] = len(moves)
        result["primitive_length_saved"] = len(input_moves) - len(moves)
        result["work_saved"] = original["work"] - result["final_verdict"]["work"]
        result["status"] = "completed"
    except BaseException as exc:
        result.update(status="failed", exception=type(exc).__name__, detail=str(exc))
        if isinstance(exc, VerificationStopped):
            result["cap_status"].append("global_verification_cap")
        raise
    finally:
        result["wall_seconds"] = time.monotonic() - started
        result["cumulative_search_apply_calls"] = prior["search_apply_calls"] + result["search_apply_calls"]
        result["cumulative_wall_seconds"] = prior["wall_seconds"] + result["wall_seconds"]
        rt.ledger["armcase_consumption"][key] = {
            "search_apply_calls": result["cumulative_search_apply_calls"],
            "wall_seconds": result["cumulative_wall_seconds"]}
        rt.current = None
        rt.deadline = None
        rt.save_ledger()
        result_path = rt.output / ("diagnostic-arm-results.json" if group == "diagnostic" else group + "-results.json")
        all_results = read(result_path, [])
        all_results.append(result)
        dump(result_path, all_results)
    return result


def selfcheck(rt):
    rt.phase = "diagnostic_search"
    checks, failures = [], []
    total = 0
    # Every freely reduced h of length <=2 at rank2 and rank3, both signs,
    # every ordered target/donor pair; independent algebraic endpoint oracle.
    for rank in (2, 3):
        state = ((1, 2, 1), (2, -1, 2)) + (((3, 1, -3),) if rank == 3 else ())
        for i in range(rank):
            for j in range(rank):
                if i == j:
                    continue
                for sign in (1, -1):
                    v = state[j] if sign == 1 else word_inverse(state[j])
                    for h in h_words(rank):
                        w = independent_reduce(h + v + word_inverse(h))
                        expected = list(state)
                        expected[i] = independent_reduce(w + state[i] + word_inverse(w))
                        expected = tuple(expected)
                        route = donor_compile(rt, i, j, sign, h)
                        observed = state
                        for move in route:
                            observed, reason = rt.stable.apply_move(observed, move)
                            assert reason is None
                            assert all(observed[k] == state[k] for k in range(rank) if k != i)
                        assert observed == expected
                        challenge = {"challenge_id": f"synthetic-r{rank}-{total}",
                                     "move_spec_version": rt.stable.MOVE_SPEC_VERSION,
                                     "initial_relators": state_json(state), "target_relators": state_json(expected)}
                        verdict = rt.verify(challenge, route, "diagnostic")
                        assert verdict["ok"] and verdict["length"] == 2 * len(h) + 4
                        total += 1
                    route = left_compile(rt, i, j, sign)
                    expected = list(state)
                    expected[i] = independent_reduce(v + state[i])
                    observed = state
                    for move in route:
                        observed, reason = rt.stable.apply_move(observed, move)
                        assert reason is None
                    assert observed == tuple(expected)
        checks.append({"rank": rank, "all_h_length_at_most_2": True,
                       "all_ordered_target_donor_pairs": True, "both_signs": True})
    state = ((2,), (1,) * 12)
    expected = (independent_reduce((1,) * 12 + (2,) + (-1,) * 12), state[1])
    challenge = {"challenge_id": "synthetic-12-to-4", "move_spec_version": rt.stable.MOVE_SPEC_VERSION,
                 "initial_relators": state_json(state), "target_relators": state_json(expected)}
    baseline = optimize(rt, challenge, [6] * 12, "baseline", "diagnostic")
    whole = optimize(rt, challenge, [6] * 12, "whole_object", "diagnostic")
    assert baseline["final_length"] == 12
    assert whole["final_length"] == 4
    assert whole["final_verdict"]["ok"]
    # Algebraically equal endpoint can still violate the resource guard.
    guard = {"challenge_id": "synthetic-resource-guard", "move_spec_version": rt.stable.MOVE_SPEC_VERSION,
             "initial_relators": [[1] * 9992, [1] * 5], "target_relators": [[1] * 9992, [1] * 5]}
    legal = rt.verify(guard, [6] * 5, "diagnostic")
    illegal = rt.verify(guard, list(donor_compile(rt, 0, 1, 1)), "diagnostic")
    assert legal["ok"] and not illegal["ok"] and illegal["code"] == "E_LENGTH_LIMIT"
    report = {"status": "passed", "identity_instances": total, "coverage": checks,
              "script_sha256": sha(Path(__file__).read_bytes()), "config_sha256": json_sha(CONFIG),
              "synthetic_12_to_4": {"baseline": baseline["final_verdict"], "whole_object": whole["final_verdict"]},
              "resource_guard": {"literal": legal, "compiled": illegal}, "unexpected_failures": failures}
    dump(rt.output / "selfcheck.json", report)
    return report


def records_for(rt, ids):
    allow = set(ids)
    # Access moves only after membership filter, never for excluded records.
    records = {r["training_id"]: r for r in rt.training_metadata()["instances"] if r["training_id"] in allow}
    assert set(records) == allow
    manifest = json.loads(rt.checked_bytes["competition/examples/training_manifest.json"])
    challenges = {c["challenge_id"]: c for c in manifest["challenges"]}
    output = []
    for ident in ids:
        challenge = challenge_for(records[ident])
        official = challenges[challenge["challenge_id"]]
        for field in ("initial_relators", "target_relators", "move_spec_version"):
            assert challenge[field] == official[field], "training/source manifest disagreement"
        challenge["instance_hash"] = official["instance_hash"]
        output.append((challenge, records[ident]["moves"]))
    return output


def run_records(rt, records, group):
    existing = read(rt.output / (group + "-results.json"), [])
    done = {(r["case_id"], r["arm"]) for r in existing if r.get("status") == "completed"}
    for challenge, moves in records:
        for arm in ("baseline", "whole_object"):
            if (challenge["challenge_id"], arm) in done:
                raise RuntimeError("refusing silent repeated completed armcase; retain existing attempt and explicitly version any rerun")
            result = optimize(rt, challenge, moves, arm, group)
            print(json.dumps({"group": group, "id": result["case_id"], "arm": arm,
                              "before": result["original_length"], "after": result["final_length"],
                              "search_apply": result["search_apply_calls"], "caps": result["cap_status"]}), flush=True)


def development(rt):
    check = read(rt.output / "selfcheck.json")
    assert check and check["status"] == "passed", "run selfcheck before development"
    records = records_for(rt, rt.protocol["development_ids"])
    manifest = json.loads((rt.source_root / "competition/tools/verifier/data/manifest.json").read_text())
    incumbent = rt.protocol["scored_incumbent_case"]
    real = next(c for c in manifest["challenges"] if c["challenge_id"] == incumbent["challenge_id"])
    assert real["target_relators"] == []
    records.append((challenge_for(real), incumbent["moves"]))
    run_records(rt, records, "development")


def freeze(rt):
    path = rt.output / "FREEZE.json"
    if path.exists():
        raise RuntimeError("freeze already exists; no overwrite permitted")
    dev = read(rt.output / "development-results.json", [])
    assert len(dev) == 10 and all(r.get("status") == "completed" for r in dev)
    assert all(r["script_sha256"] == sha(Path(__file__).read_bytes()) and r["config_sha256"] == json_sha(CONFIG) for r in dev), "development executed with a different code/config; disclose/version before freezing"
    check = read(rt.output / "selfcheck.json")
    assert check["script_sha256"] == sha(Path(__file__).read_bytes()) and check["config_sha256"] == json_sha(CONFIG), "selfcheck code/config mismatch"
    excluded = set(rt.protocol["development_ids"]) | set(rt.protocol["reserved_prior_evaluation_ids_excluded"])
    choices = []
    for record in rt.training_metadata()["instances"]:
        ident, length = record["training_id"], record["length"]
        if ident in excluded or length > CONFIG["maximum_test_original_length"]:
            continue
        digest = sha((PIN + "|" + ident + "|" + CONFIG["selection_salt"]).encode())
        choices.append((digest, ident, length))
    selected = sorted(choices)[:CONFIG["test_count"]]
    assert len(selected) == 16
    value = {
        "frozen_at": now(), "version": CONFIG["version"],
        "script_sha256": sha(Path(__file__).read_bytes()),
        "config_sha256": json_sha(CONFIG), "config": CONFIG,
        "protocol_sha256": sha(rt.protocol_path.read_bytes()),
        "source_hashes": rt.source_hashes,
        "selected_public_training_tests": [{"training_id": ident, "selection_sha256": digest, "declared_length": length} for digest, ident, length in selected],
        "development_ids": rt.protocol["development_ids"],
        "reserved_prior_evaluation_ids_excluded": rt.protocol["reserved_prior_evaluation_ids_excluded"],
        "development_results_sha256": sha((rt.output / "development-results.json").read_bytes()),
        "selfcheck_sha256": sha((rt.output / "selfcheck.json").read_bytes()),
        "declaration": "selected test move arrays have not been indexed, inspected, replayed, or analyzed by this application before this freeze; metadata selection only",
        "selection_pool_count": len(choices), "counter_snapshot": dict(rt.counters),
    }
    dump(path, value)
    return value


def test(rt):
    frozen = read(rt.output / "FREEZE.json")
    assert frozen, "freeze before new-test move access"
    assert frozen["script_sha256"] == sha(Path(__file__).read_bytes()), "post-freeze implementation change"
    assert frozen["config_sha256"] == json_sha(CONFIG), "post-freeze config change"
    assert frozen["protocol_sha256"] == sha(rt.protocol_path.read_bytes()), "post-freeze protocol change"
    assert frozen["source_hashes"] == rt.source_hashes
    ids = [r["training_id"] for r in frozen["selected_public_training_tests"]]
    access_path = rt.output / "TEST-ACCESS.json"
    if access_path.exists():
        raise RuntimeError("test previously accessed; no silent restart allowed")
    dump(access_path, {"first_move_array_access_at": now(),
                       "freeze_sha256": sha((rt.output / "FREEZE.json").read_bytes()),
                       "script_sha256": sha(Path(__file__).read_bytes()), "ids": ids})
    run_records(rt, records_for(rt, ids), "test")


def report(rt):
    dev = read(rt.output / "development-results.json", [])
    tests = read(rt.output / "test-results.json", [])
    rows = dev + tests
    complete = len(rows) == 42 and all(r.get("status") == "completed" for r in rows)
    grouped = defaultdict(list)
    for r in rows:
        grouped[(r["group"], r["case_id"])].append(r)
    comparisons = []
    for (group, ident), values in grouped.items():
        arms = {r["arm"]: r for r in values}
        if len(arms) != 2:
            continue
        a, b = arms["baseline"], arms["whole_object"]
        comparisons.append({"group": group, "case_id": ident, "original_length": a["original_length"],
                            "baseline_length": a["final_length"], "whole_object_length": b["final_length"],
                            "whole_object_extra_length_saved": a["final_length"] - b["final_length"],
                            "baseline_work": a["final_verdict"]["work"], "whole_object_work": b["final_verdict"]["work"],
                            "baseline_search_apply": a["search_apply_calls"], "whole_object_search_apply": b["search_apply_calls"]})
    totals = {}
    for arm in ("baseline", "whole_object"):
        armrows = [r for r in rows if r["arm"] == arm and r.get("status") == "completed"]
        totals[arm] = {"completed_armcases": len(armrows),
                       "original_primitive_length": sum(r["original_length"] for r in armrows),
                       "final_primitive_length": sum(r["final_length"] for r in armrows),
                       "primitive_length_saved": sum(r["primitive_length_saved"] for r in armrows),
                       "improved_cases": sum(r["primitive_length_saved"] > 0 for r in armrows),
                       "accepted_rewrites": sum(len(r["accepted"]) for r in armrows),
                       "search_apply_calls": sum(r["search_apply_calls"] for r in armrows),
                       "verification_apply_calls": sum(r["verification_apply_calls"] for r in armrows),
                       "cap_armcases": sum(bool(r["cap_status"]) for r in armrows),
                       "verification_failures": sum(len(r["verification_failures"]) for r in armrows)}
    armcase_search_total = sum(v for k, v in rt.counters.items() if k in ("development_search_apply", "test_search_apply"))
    search_total = sum(v for k, v in rt.counters.items() if k.endswith("search_apply"))
    verification_total = sum(v for k, v in rt.counters.items() if k.endswith("verification_apply"))
    assert search_total <= CONFIG["total_armcase_search_apply_cap"]
    assert verification_total <= CONFIG["application_verification_apply_cap_including_diagnostics"]
    output = {
        "status": "complete" if complete else "incomplete", "generated_at": now(),
        "purpose": CONFIG["scope"], "frozen_test": read(rt.output / "FREEZE.json"),
        "armcase_count": len(rows), "summary": totals, "paired_comparisons": comparisons,
        "accounting": {"armcase_search_apply_calls_including_development_retries": armcase_search_total,
                       "all_search_apply_calls_including_diagnostics_and_retries": search_total,
                       "all_search_apply_cap": CONFIG["total_armcase_search_apply_cap"],
                       "all_verification_apply_calls_including_diagnostics": verification_total,
                       "all_verification_apply_cap": CONFIG["total_verification_apply_cap_including_diagnostics"],
                       "application_verification_apply_cap": CONFIG["application_verification_apply_cap_including_diagnostics"],
                       "external_reserved_verification_apply": CONFIG["external_verification_apply_reservations"],
                       "diagnostic_search_apply_calls": rt.counters["diagnostic_search_apply"],
                       "all_phase_counters": dict(rt.counters)},
        "budget_interpretation": "identical per-armcase allowance (50000 official search applies, 15 seconds, <=3 accepted rewrites); actual expenditures differ. Wall time is descriptive only; truncated rounds would rank only enumerated candidates.",
        "armcases": rows,
    }
    dump(rt.output / "results.json", output)
    dump(rt.output / "PROVENANCE.json", rt.provenance())
    improved = []
    for r in rows:
        if r.get("status") == "completed" and r["primitive_length_saved"] > 0:
            improved.append({"challenge_id": r["case_id"], "group": r["group"], "arm": r["arm"],
                             "move_spec_version": rt.stable.MOVE_SPEC_VERSION, "moves": r["final_moves"],
                             "official_verdict": r["final_verdict"]})
    if improved:
        dump(rt.output / "improved-certificates.json", improved)
        real = [r for r in improved if r["challenge_id"] == "sac-07445"]
        if real:
            best = min(real, key=lambda r: (r["official_verdict"]["length"], r["official_verdict"]["work"], r["official_verdict"]["peak_total_relator_length"], r["moves"]))
            (rt.output / "sac-07445-submission.txt").write_text(best["challenge_id"] + ": " + json.dumps(best["moves"]) + "\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("selfcheck", "development", "freeze", "test", "report"))
    parser.add_argument("--source-root", type=Path, default=HERE.parents[1] / "ac_official")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    rt = Runtime(args.source_root.resolve(), args.output.resolve())
    with rt.attempt(args.command):
        output = globals()[args.command](rt)
        if output is not None:
            print(json.dumps({"command": args.command, "status": output.get("status", "completed")}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
