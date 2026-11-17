#!/usr/bin/env python3
"""Finite exact-state Stable-AC tail synthesis, standard library only.

Run development, freeze, test, report in that order. Public test move lists
are indexed only by test, after code/config/selected-ID hashes are frozen.
"""
import argparse
from collections import Counter, deque
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
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
    "competition/tools/verifier/canon.py": "93175152acd876566ff60bbfaf7cd90cd8cd2fa9",
    "competition/tools/verifier/core.py": "0a5da5fe6e3e42c96877734dad46b155a69c02b2",
    "competition/tools/verifier/stable_core.py": "af48e32f766dbcd0cad0becd8c1c4edb4358efac",
    "competition/examples/stable_training_424.json": "22428166cb348d41bbc92e24ab9e2a49e1ebd235",
    "competition/tools/verifier/data/manifest.json": "accdb626ee08a06beea3f88dc7f351514c99eb27",
}
CONFIG = {
    "version": "goal-aware-tail-bfs-v1",
    "maximum_original_tail_length": 6,
    "maximum_entry_rank": 2,
    "maximum_entry_total_length": 12,
    "maximum_replacement_length": 5,
    "search_apply_per_case": 15000,
    "search_apply_global": 500000,
    "verification_apply_global": 15000,
    "entry_order": "ascending original prefix position (old suffix lengths 6 down to 2)",
    "entry_budget": "floor(remaining case apply / remaining eligible entries), no carry backwards",
    "move_order": "destabilize IDs ascending, then applicable-rank inversion/multiplication/conjugation IDs ascending",
    "rank_policy": "no stabilization; rank never increases; rank<=2 throughout search",
    "depth_policy": "replacement strictly shorter than old tail; at most 5; rank lower bound prunes",
    "state_policy": "exact freely reduced ordered tuple including rank; no quotient or rename",
    "dominance": "same state: keep Pareto labels (depth, added-work, local-peak); first path retained on equal labels",
    "local_length_policy": "official max_total_relator_length only; local length increases permitted",
    "candidate_choice": "full length, full work, full peak, prefix position, replacement move tuple",
    "limits": {"max_path_length": 100000, "max_total_relator_length": 10000, "max_work": 5000000},
    "claim_scope": "bounded certificate postprocessing; not a from-scratch solver, global optimality, or literature novelty claim",
}

def now():
    return datetime.now(timezone.utc).isoformat()

def sha(data):
    return hashlib.sha256(data).hexdigest()

def jsha(obj):
    return sha(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode())

def gitblob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()

def dump(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")) + "\n")

def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default

def total(state):
    return sum(map(len, state))

class BudgetStop(Exception):
    pass

class Runtime:
    def __init__(self, official):
        self.official = official
        self.protocol = read(HERE.parent / "PROTOCOL.json")
        self.source = {}
        checked = {}
        for rel, expected in BLOBS.items():
            data = (official / rel).read_bytes()
            if gitblob(data) != expected:
                raise RuntimeError("official Git blob mismatch: " + rel)
            checked[rel] = data
            self.source[rel] = {"git_blob": expected, "sha256": sha(data)}
        pkgname = "_goal_suffix_pinned"
        pkg = types.ModuleType(pkgname)
        pkg.__path__ = [str(official / "competition/tools/verifier")]
        sys.modules[pkgname] = pkg
        for name in ("canon", "core", "stable_core"):
            m = types.ModuleType(pkgname + "." + name)
            m.__package__ = pkgname
            m.__file__ = str(official / "competition/tools/verifier" / (name + ".py"))
            sys.modules[m.__name__] = m
            setattr(pkg, name, m)
            exec(compile(checked["competition/tools/verifier/" + name + ".py"], m.__file__, "exec"), m.__dict__)
        self.stable = pkg.stable_core
        self.ledger = read(HERE / "attempt-ledger.json", {"attempts": [], "counts": {}, "case_search": {}})
        self.counts = Counter(self.ledger["counts"])
        self.phase = "unassigned"
        self.case = None
        self.local_stop = None
        original = self.stable.apply_move
        def counted(state, move):
            if self.phase.endswith("search"):
                if self.search_used() >= CONFIG["search_apply_global"]:
                    raise BudgetStop("global_search_apply_cap")
                if self.case is not None:
                    used = self.ledger["case_search"].get(self.case, 0)
                    if used >= CONFIG["search_apply_per_case"]:
                        raise BudgetStop("case_search_apply_cap_including_retries")
                if self.local_stop is not None and self.search_used() >= self.local_stop:
                    raise BudgetStop("entry_search_apply_cap")
            elif self.phase.endswith("verification"):
                if self.verify_used() >= CONFIG["verification_apply_global"]:
                    raise BudgetStop("global_verification_apply_cap")
            else:
                raise RuntimeError("uncategorized official apply")
            self.counts[self.phase + "_apply"] += 1
            if self.phase.endswith("search") and self.case is not None:
                self.ledger["case_search"][self.case] = self.ledger["case_search"].get(self.case, 0) + 1
            return original(state, move)
        self.stable.apply_move = counted
        self.moves = {}
        for rank in (0, 1, 2):
            ds, others = [], []
            for row in self.stable.MOVE_TABLE:
                cat = row["category"]
                if cat == "stabilize" or row.get("relator", rank) >= rank:
                    continue
                if cat == "multiplication" and row["other"] >= rank:
                    continue
                if cat == "conjugation" and abs(row["conjugator"]) > rank:
                    continue
                (ds if cat == "destabilize" else others).append(row["id"])
            self.moves[rank] = (tuple(ds), tuple(others))

    def search_used(self):
        return sum(v for k, v in self.counts.items() if k.endswith("search_apply"))

    def verify_used(self):
        return sum(v for k, v in self.counts.items() if k.endswith("verification_apply"))

    def save(self):
        self.ledger["counts"] = dict(self.counts)
        dump(HERE / "attempt-ledger.json", self.ledger)

    @contextmanager
    def attempt(self, command):
        a = {"command": command, "started": now(), "script_sha256": sha(Path(__file__).read_bytes()),
             "config_sha256": jsha(CONFIG), "before": dict(self.counts)}
        self.ledger["attempts"].append(a)
        self.save()
        try:
            yield
            a["status"] = "completed"
        except BaseException as exc:
            a.update(status="failed", error=str(exc), traceback=traceback.format_exc())
            raise
        finally:
            a.update(finished=now(), after=dict(self.counts), consumed=dict(self.counts - Counter(a["before"])))
            self.save()

    def verify(self, challenge, moves, phase):
        if self.verify_used() + len(moves) > CONFIG["verification_apply_global"]:
            raise BudgetStop("verification_full_path_reservation")
        self.phase = phase + "_verification"
        return self.stable.verify(challenge, list(moves), self.stable.MOVE_SPEC_VERSION, CONFIG["limits"])

    def trace(self, challenge, moves, phase):
        if self.verify_used() + len(moves) > CONFIG["verification_apply_global"]:
            raise BudgetStop("verification_full_trace_reservation")
        self.phase = phase + "_verification"
        states = [tuple(tuple(w) for w in challenge["initial_relators"])]
        for m in moves:
            nxt, reason = self.stable.apply_move(states[-1], m)
            if reason:
                raise RuntimeError("trace inapplicable: " + reason)
            states.append(nxt)
        return states

    def training(self, ids):
        # Decode public JSON, but index moves only for the explicitly requested IDs.
        data = json.loads((self.official / "competition/examples/stable_training_424.json").read_text())
        metadata = {r["training_id"]: r for r in data["instances"]}
        out = []
        for sid in ids:
            r = metadata[sid]
            c = {"challenge_id": sid.replace("ms-train-", "sac-train-"), "source_training_id": sid,
                 "initial_relators": r["initial_relators"], "target_relators": [],
                 "move_spec_version": "sac-r8-v1"}
            out.append((sid, c, r["moves"]))
        return out

    def scored(self):
        item = self.protocol["old_scored_incumbent"]
        manifest = json.loads((self.official / "competition/tools/verifier/data/manifest.json").read_text())
        c = next(c for c in manifest["challenges"] if c["challenge_id"] == item["id"])
        return item["id"], c, item["moves"]

def suffix_search(rt, entry, maximum_depth, prefix_work, prefix_peak):
    # BFS labels retain sufficient resource information for safe dominance.
    q = deque([(entry, (), 0, total(entry))])
    labels = {entry: [(0, 0, total(entry))]}
    stats = {"expanded": 0, "generated": 0, "inapplicable": {}, "rank_pruned": 0,
             "resource_pruned": 0, "dominated": 0, "label_count": 1, "found": 0,
             "exhausted": True, "stop": "queue_exhausted", "maximum_depth": maximum_depth}
    best = None
    while q:
        state, path, work, peak = q.popleft()
        depth = len(path)
        bound = maximum_depth if best is None else len(best[0])
        if depth + len(state) > bound or depth >= bound:
            stats["rank_pruned"] += 1
            continue
        stats["expanded"] += 1
        ds, others = rt.moves[len(state)]
        moves = ds if depth + len(state) == bound else ds + others
        for m in moves:
            try:
                nxt, reason = rt.stable.apply_move(state, m)
            except BudgetStop as exc:
                stats.update(exhausted=False, stop=str(exc))
                return best, stats
            stats["generated"] += 1
            if reason:
                stats["inapplicable"][reason] = stats["inapplicable"].get(reason, 0) + 1
                continue
            nd, nw, np = depth + 1, work + total(nxt), max(peak, total(nxt))
            if prefix_work + nw > CONFIG["limits"]["max_work"] or max(prefix_peak, np) > CONFIG["limits"]["max_total_relator_length"]:
                stats["resource_pruned"] += 1
                continue
            if nd + len(nxt) > bound:
                stats["rank_pruned"] += 1
                continue
            route = path + (m,)
            if not nxt:
                stats["found"] += 1
                cand = (route, nw, np)
                if best is None or (len(route), nw, np, route) < (len(best[0]), best[1], best[2], best[0]):
                    best = cand
                continue
            old = labels.setdefault(nxt, [])
            if any(d <= nd and w <= nw and p <= np for d, w, p in old):
                stats["dominated"] += 1
                continue
            old[:] = [(d, w, p) for d, w, p in old if not (nd <= d and nw <= w and np <= p)]
            old.append((nd, nw, np))
            stats["label_count"] += 1
            q.append((nxt, route, nw, np))
    return best, stats

def mechanism(rt, entry, replacement):
    cats = [rt.stable.MOVE_TABLE[m]["category"] for m in replacement]
    # Signed-permutation inversion followed by deletion is conservatively grouped
    # with known direct-deletion rather than advertised as a new mechanism.
    letters = [w[0] for w in entry if len(w) == 1]
    signed_perm = len(letters) == len(entry) and len({abs(a) for a in letters}) == len(entry)
    if signed_perm and all(c in ("inversion", "destabilize") for c in cats):
        return "old_direct_deletion"
    if "multiplication" in cats:
        return "elimination_candidate"
    return "other"

def run_case(rt, sid, challenge, original, group, old_baseline):
    rt.case, rt.local_stop = sid, None
    before = Counter(rt.counts)
    result = {"source_id": sid, "challenge": challenge, "group": group,
              "original_moves": original, "old_baseline": old_baseline,
              "entries": [], "candidate_count": 0, "status": "completed"}
    ov = rt.verify(challenge, original, group)
    if not ov["ok"]:
        raise RuntimeError("original failed: " + str(ov))
    result["original_verdict"] = ov
    states = rt.trace(challenge, original, group + "_trace")
    lens = [total(s) for s in states]
    pref = []
    for length in lens:
        pref.append(length + (pref[-1] if pref else 0))
    entries = []
    for a in range(max(0, len(original) - CONFIG["maximum_original_tail_length"]), len(original)):
        st = states[a]
        maxdepth = min(CONFIG["maximum_replacement_length"], len(original) - a - 1)
        if 1 <= len(st) <= CONFIG["maximum_entry_rank"] and total(st) <= CONFIG["maximum_entry_total_length"] and maxdepth >= len(st):
            entries.append((a, maxdepth))
    candidates = []
    for index, (a, maxdepth) in enumerate(entries):
        remaining = max(0, CONFIG["search_apply_per_case"] - rt.ledger["case_search"].get(sid, 0))
        local_budget = remaining // (len(entries) - index)
        rt.local_stop = rt.search_used() + local_budget
        rt.phase = group + "_search"
        entry = states[a]
        sbefore = rt.search_used()
        found, stats = suffix_search(rt, entry, maxdepth, pref[a], max(lens[:a + 1]))
        item = {"prefix_length": a, "entry_tuple": entry, "entry_rank": len(entry),
                "entry_total_length": total(entry), "removed_moves": original[a:],
                "allocated_search_apply": local_budget, "actual_search_apply": rt.search_used() - sbefore,
                "search": stats, "replacement_moves": None}
        if found is not None:
            route, added_work, local_peak = found
            full = original[:a] + list(route)
            predicted = {"length": len(full), "work": pref[a] + added_work,
                         "peak_total_relator_length": max(max(lens[:a + 1]), local_peak)}
            kind = mechanism(rt, entry, route)
            item.update(replacement_moves=route, mechanism=kind, predicted_full_metrics=predicted)
            key = (len(full), predicted["work"], predicted["peak_total_relator_length"], a, route)
            candidates.append((key, full, item))
        result["entries"].append(item)
    result["candidate_count"] = len(candidates)
    rt.local_stop = None
    final, fv = list(original), ov
    if candidates:
        _, final, selected = min(candidates, key=lambda x: x[0])
        fv = rt.verify(challenge, final, group + "_candidate")
        if not fv["ok"]:
            result.update(status="candidate_rejected", failed_candidate_moves=final, failed_verdict=fv)
            final, fv = list(original), ov
        else:
            for key, val in selected["predicted_full_metrics"].items():
                if fv[key] != val:
                    raise RuntimeError("full metric mismatch: " + key)
            result["selected"] = selected
            # Retain every exact state and rank of the accepted new certificate.
            trace = rt.trace(challenge, final, group + "_final_trace")
            result["final_trace"] = [{"tuple": s, "rank": len(s), "total_length": total(s)} for s in trace]
    result.update(final_moves=final, final_verdict=fv, length_saved=ov["length"] - fv["length"],
                  work_saved=ov["work"] - fv["work"],
                  old_baseline_length_difference=None if old_baseline is None else len(old_baseline["moves"]) - len(final),
                  consumed=dict(rt.counts - before), cumulative_case_search=rt.ledger["case_search"].get(sid, 0))
    rt.case = None
    rt.save()
    return result

def baselines():
    old = read(HERE.parent.parent / "proof_reconstruction_round2_20261117/application/results.json")
    return {r["source_training_id"] or r["case_id"]: {"moves": r["final_moves"], "verdict": r["final_verdict"]}
            for r in old["armcases"] if r["arm"] == "baseline"}

def freeze(rt):
    if (HERE / "TEST-ACCESS.json").exists():
        raise RuntimeError("refuse refreeze after test access")
    tests = rt.protocol["new_public_training_test"]
    data = {"frozen_at": now(), "script_sha256": sha(Path(__file__).read_bytes()), "config": CONFIG,
            "config_sha256": jsha(CONFIG), "official_sources": rt.source,
            "selected_tests": tests, "selected_ids_sha256": jsha([t["id"] for t in tests]),
            "protocol_sha256": sha((HERE.parent / "PROTOCOL.json").read_bytes()),
            "development_results_sha256": sha((HERE / "development-results.json").read_bytes()),
            "counts_before_test": dict(rt.counts)}
    dump(HERE / "FREEZE.json", data)

def report(rt):
    dev = read(HERE / "development-results.json", [])
    tests = read(HERE / "test-results.json", [])
    scored = read(HERE / "scored-results.json", [])
    rows = dev + tests + scored
    summaries = {}
    for group in ("development", "test", "old_scored"):
        rr = [r for r in rows if r["group"] == group]
        summaries[group] = {"count": len(rr), "original_length": sum(r["original_verdict"]["length"] for r in rr),
                            "final_length": sum(r["final_verdict"]["length"] for r in rr),
                            "length_saved": sum(r["length_saved"] for r in rr),
                            "improved_cases": sum(r["length_saved"] > 0 for r in rr),
                            "selected_mechanisms": dict(Counter(r["selected"]["mechanism"] for r in rr if "selected" in r)),
                            "search_apply": sum(v for r in rr for k, v in r["consumed"].items() if k.endswith("search_apply")),
                            "verification_apply": sum(v for r in rr for k, v in r["consumed"].items() if k.endswith("verification_apply"))}
    dump(HERE / "results.json", {"generated_at": now(), "status": "complete" if len(rows) == 29 else "partial",
                                "config": CONFIG, "summary": summaries, "accounting": dict(rt.counts),
                                "total_search_apply": rt.search_used(), "total_verification_apply": rt.verify_used(),
                                "all_cases": rows})
    improved = [{"source_id": r["source_id"], "challenge": r["challenge"], "moves": r["final_moves"],
                 "verdict": r["final_verdict"], "selected": r.get("selected")}
                for r in rows if r["length_saved"] > 0]
    dump(HERE / "improved-certificates.json", improved)
    print(json.dumps(summaries, ensure_ascii=False, indent=2))
    print("total search", rt.search_used(), "verification", rt.verify_used())

def main():
    p = argparse.ArgumentParser()
    p.add_argument("command", choices=("development", "freeze", "test", "report"))
    p.add_argument("--official-root", type=Path, default=HERE.parent.parent / "ac_official")
    args = p.parse_args()
    rt = Runtime(args.official_root)
    with rt.attempt(args.command):
        if args.command == "development":
            if (HERE / "TEST-ACCESS.json").exists():
                raise RuntimeError("no development after test access")
            old = baselines()
            out = []
            for sid, c, moves in rt.training(rt.protocol["known_development_training_ids"]):
                r = run_case(rt, sid, c, moves, "development", old.get(sid))
                out.append(r)
                dump(HERE / "development-results.json", out)
                print(sid, r["original_verdict"]["length"], "->", r["final_verdict"]["length"],
                      r.get("selected", {}).get("mechanism"), "search", r["cumulative_case_search"])
            sid, c, moves = rt.scored()
            dump(HERE / "scored-results.json", [run_case(rt, sid, c, moves, "old_scored", old.get(sid))])
        elif args.command == "freeze":
            freeze(rt)
        elif args.command == "test":
            fr = read(HERE / "FREEZE.json")
            if fr is None or fr["script_sha256"] != sha(Path(__file__).read_bytes()) or fr["config_sha256"] != jsha(CONFIG):
                raise RuntimeError("freeze code/config mismatch")
            if fr["protocol_sha256"] != sha((HERE.parent / "PROTOCOL.json").read_bytes()):
                raise RuntimeError("protocol changed after freeze")
            access = {"first_action_list_access_after": now(), "script_sha256": fr["script_sha256"],
                      "config_sha256": fr["config_sha256"], "selected_ids_sha256": fr["selected_ids_sha256"],
                      "selected_ids": [t["id"] for t in fr["selected_tests"]],
                      "statement": "written before selected new8 move arrays are indexed; old v1 four are never indexed"}
            if not (HERE / "TEST-ACCESS.json").exists():
                dump(HERE / "TEST-ACCESS.json", access)
            out = []
            for sid, c, moves in rt.training(access["selected_ids"]):
                r = run_case(rt, sid, c, moves, "test", None)
                out.append(r)
                dump(HERE / "test-results.json", out)
                print(sid, r["original_verdict"]["length"], "->", r["final_verdict"]["length"],
                      r.get("selected", {}).get("mechanism"), "search", r["cumulative_case_search"])
        else:
            report(rt)

if __name__ == "__main__":
    main()
