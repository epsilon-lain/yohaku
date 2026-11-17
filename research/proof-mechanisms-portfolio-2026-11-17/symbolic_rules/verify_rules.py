#!/usr/bin/env python3
"""Hash-locked official replay of frozen symbolic rules and whole certificates.

No search. All successful and failed official apply calls are counted.
"""
import hashlib
import json
import sys
import types
from collections import Counter
from pathlib import Path

from discover_rules import invert, reduce_word

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]
OFFICIAL = WORKSPACE / "ac_official"
LOCK = WORKSPACE / "proof_reconstruction_round2_20261117/OFFICIAL-SOURCE-LOCK.json"
RULES_HASH = "701b9b233a7ba0a1e926d0333ae8fef652e6c9bd83ab4a6ef12070bbd617e2bc"
LIMITS = {"max_path_length": 100000, "max_total_relator_length": 10000, "max_work": 5000000}
CAP = 5000


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git_blob(data):
    return hashlib.sha1(("blob %d\0" % len(data)).encode() + data).hexdigest()


def load_official():
    lock = json.loads(LOCK.read_text())
    checked = []
    for row in lock["files"]:
        data = (OFFICIAL / row["path"]).read_bytes()
        assert hashlib.sha256(data).hexdigest() == row["sha256"], row["path"]
        assert git_blob(data) == row["git_blob"], row["path"]
        checked.append({"path": row["path"], "git_blob": row["git_blob"], "sha256": row["sha256"]})
    pkgname = "_portfolio_symbolic_official"
    package = types.ModuleType(pkgname)
    package.__path__ = []
    sys.modules[pkgname] = package
    loaded = {}
    for name in ("canon", "core", "stable_core"):
        fullname = pkgname + "." + name
        path = OFFICIAL / ("competition/tools/verifier/" + name + ".py")
        module = types.ModuleType(fullname)
        module.__package__ = pkgname
        module.__file__ = str(path)
        sys.modules[fullname] = module
        setattr(package, name, module)
        exec(compile(path.read_bytes(), str(path), "exec"), module.__dict__)
        loaded[name] = module
    return loaded["stable_core"], checked


def metrics(states):
    lengths = [sum(len(word) for word in state) for state in states]
    return {"length": len(states) - 1, "work": sum(lengths), "peak_total_relator_length": max(lengths), "total_length_by_state": lengths}


def state_hashes(states):
    return [hashlib.sha256(json.dumps(s, separators=(",", ":")).encode()).hexdigest() for s in states]


def challenge_for(record):
    return {"challenge_id": record["training_id"].replace("ms-train-", "sac-train-"),
            "move_spec_version": "sac-r8-v1", "initial_relators": record["initial_relators"],
            "target_relators": record["target_relators"]}


def substitute(signature, state):
    image = {1: (1,), 2: (2,), 3: state[0], 4: state[1]}
    result = []
    for word in signature:
        output = ()
        for letter in word:
            part = image[abs(letter)]
            output += part if letter > 0 else invert(part)
        result.append(reduce_word(output))
    return tuple(result)


class Runtime:
    def __init__(self, stable):
        self.stable = stable
        self.phase = "unset"
        self.calls = Counter()
        self.raw_apply = stable.apply_move
        stable.apply_move = self.apply

    def apply(self, state, move):
        if sum(self.calls.values()) >= CAP:
            raise RuntimeError("official verification apply budget exhausted")
        self.calls[self.phase] += 1
        return self.raw_apply(state, move)

    def replay(self, initial, moves, phase):
        self.phase = phase
        state = tuple(tuple(w) for w in initial)
        states = [state]
        for move in moves:
            state, reason = self.apply(state, move)
            assert reason is None, (phase, move, reason)
            states.append(state)
        return states

    def verify(self, challenge, moves, phase):
        self.phase = phase
        return self.stable.verify(challenge, list(moves), "sac-r8-v1", LIMITS)


def run():
    assert sha(HERE / "RULES.json") == RULES_HASH
    rules = json.loads((HERE / "RULES.json").read_text())["rules"]
    records = json.loads((HERE / "DEVELOPMENT-INPUT.json").read_text())["records"]
    protocol = json.loads((HERE.parent / "PROTOCOL.json").read_text())
    assert {r["training_id"] for r in records} == set(protocol["known_development_training_ids"])
    stable, checked = load_official()
    rt = Runtime(stable)
    original_states, originals = {}, []
    certificates, candidate_results = [], []
    for record in records:
        ident = record["training_id"]
        states = rt.replay(record["initial_relators"], record["moves"], "development_original_step_replay")
        verdict = rt.verify(challenge_for(record), record["moves"], "development_original_full_verify")
        assert verdict["ok"] and states[-1] == ()
        expected = metrics(states)
        for key in ("length", "work", "peak_total_relator_length"):
            assert expected[key] == verdict[key] == record[key]
        original_states[ident] = states
        originals.append({"training_id": ident, "official_verdict": verdict, "metrics": expected,
                          "state_hashes": state_hashes(states)})
    by_id = {r["training_id"]: r for r in records}
    for rule in rules:
        for source in rule["sources"]:
            record = by_id[source["training_id"]]
            start, end = source["start"], source["end_exclusive"]
            assert record["moves"][start:end] == rule["old_moves"]
            moves = record["moves"][:start] + rule["new_moves"] + record["moves"][end:]
            initial = record["initial_relators"]
            states = rt.replay(initial, moves, "development_candidate_step_replay")
            old_states = original_states[record["training_id"]]
            assert states[start] == old_states[start]
            assert states[start + len(rule["new_moves"])] == old_states[end]
            assert states[-1] == ()
            verdict = rt.verify(challenge_for(record), moves, "development_candidate_full_verify")
            expected = metrics(states)
            assert verdict["ok"], verdict
            for key in ("length", "work", "peak_total_relator_length"):
                assert expected[key] == verdict[key]
            item = {"rule_id": rule["id"], **source, "official_verdict": verdict,
                    "metrics": expected, "state_hashes": state_hashes(states),
                    "old_metrics": metrics(old_states), "length_saved": len(record["moves"]) - len(moves)}
            candidate_results.append(item)
            certificates.append({"rule_id": rule["id"], **source,
                                 "challenge": challenge_for(record),
                                 "original_moves": record["moves"], "moves": moves,
                                 "official_verdict": verdict})
    synthetic_states = [
        ((), ()), ((1,), (2,)), ((-1,), (2,)),
        ((1, 2), (-2, -1)), ((1,), (2, -1)),
        ((2, 1, -2), (1, -2)), ((1, 1, -2), (-1, 2, -1)),
        ((2, -1), (-2, 1, 2)),
    ]
    synthetic_results = []
    for rule in rules:
        for index, initial in enumerate(synthetic_states):
            old_states = rt.replay(initial, rule["old_moves"], "synthetic_rule_step_replay")
            new_states = rt.replay(initial, rule["new_moves"], "synthetic_rule_step_replay")
            expected = substitute(rule["proof_symbolic_output"], initial)
            assert old_states[-1] == new_states[-1] == expected
            synthetic_results.append({"rule_id": rule["id"], "input_index": index,
                                      "initial_state": initial, "final_state": expected,
                                      "old_metrics": metrics(old_states), "new_metrics": metrics(new_states)})
    # The endpoint identity does not imply the replacement respects the length cap.
    n = 4999
    initial = ((1,), (2,) * n + (-1,))
    old_states = rt.replay(initial, [4, 2, 5, 2], "resource_counterexample_step_replay")
    new_states = rt.replay(initial, [2, 5], "resource_counterexample_step_replay")
    assert old_states[-1] == new_states[-1]
    challenge = {"challenge_id": "synthetic-symbolic-peak-guard", "move_spec_version": "sac-r8-v1",
                 "initial_relators": initial, "target_relators": old_states[-1]}
    old_verdict = rt.verify(challenge, [4, 2, 5, 2], "resource_counterexample_full_verify")
    new_verdict = rt.verify(challenge, [2, 5], "resource_counterexample_full_verify")
    assert old_verdict["ok"] and new_verdict["code"] == "E_LENGTH_LIMIT"
    guard = {"construction": "U=X, V=Y^n X^-1", "n": n,
             "old_moves": [4, 2, 5, 2], "new_moves": [2, 5],
             "old_metrics": metrics(old_states), "new_unguarded_metrics": metrics(new_states),
             "old_official_verdict": old_verdict, "new_official_verdict": new_verdict}
    best_per_case = {}
    for item in candidate_results:
        ident = item["training_id"]
        key = tuple(item["metrics"][k] for k in ("length", "work", "peak_total_relator_length"))
        prior = best_per_case.get(ident)
        if prior is None or key < tuple(prior["metrics"][k] for k in ("length", "work", "peak_total_relator_length")):
            best_per_case[ident] = item
    summary = {
        "original_full_certificates_accepted": len(originals),
        "single_rule_complete_replacements_accepted": len(candidate_results),
        "distinct_development_cases_with_replacement": len(best_per_case),
        "length_saved_best_single_rule_per_affected_case": sum(x["length_saved"] for x in best_per_case.values()),
        "best_single_rule_by_case": {ident: {"rule_id": r["rule_id"], "start": r["start"], "end_exclusive": r["end_exclusive"], "old_metrics": r["old_metrics"], "metrics": r["metrics"]} for ident, r in best_per_case.items()},
        "synthetic_rule_input_pairs_verified": len(synthetic_results),
        "official_search_apply_calls": 0,
        "official_verification_apply_calls": dict(rt.calls),
        "official_verification_apply_calls_total": sum(rt.calls.values()),
        "official_verification_apply_cap": CAP,
        "source_commit": protocol["official_commit"],
        "source_lock_files_checked": len(checked),
        "source_loading": "exec(compile(hash-checked exact source bytes)); no imports from pyc or verifier.__init__",
        "rules_sha256": RULES_HASH, "script_sha256": sha(Path(__file__)),
        "test_actions_accessed": [],
    }
    def write(name, value):
        (HERE / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    write("CERTIFICATES.json", certificates)
    write("OFFICIAL-VERIFICATION.json", {"summary": summary, "originals": originals,
          "single_replacements": candidate_results, "synthetic_rule_checks": synthetic_results,
          "resource_counterexample": guard, "checked_source_files": checked})
    print(json.dumps(summary, ensure_ascii=False))
    print(json.dumps({"resource_counterexample": guard}, ensure_ascii=False))


if __name__ == "__main__":
    run()
