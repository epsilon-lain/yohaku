#!/usr/bin/env python3
"""Fixed original-state DAG: exact-endpoint greedy versus budgeted Pareto DP.

Standard library only. Commands: selfcheck, development, freeze, test, report.
All official apply_move invocations, including failures and verify internals,
are counted persistently. Public-test moves are indexed only after FREEZE.
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


def now():
    return datetime.now(timezone.utc).isoformat()


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, separators=(",", ":")) + "\n")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def jsha(value):
    return sha(json.dumps(value, sort_keys=True, separators=(",", ":")).encode())


def blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def size(state):
    return sum(map(len, state))


def reduce_word(word):
    out = []
    for a in word:
        if out and out[-1] == -a:
            out.pop()
        else:
            out.append(a)
    return tuple(out)


def inverse(word):
    return tuple(-a for a in reversed(word))


class SearchStopped(Exception):
    pass


class Runtime:
    def __init__(self, source_root, output=HERE):
        self.root, self.output = source_root, output
        output.mkdir(parents=True, exist_ok=True)
        self.config = read(HERE / "config.json")
        self.protocol = read(HERE.parent / "PROTOCOL.json")
        self.symbolic = read(HERE / "rules-symbolic.json", {"rules": []})
        self.rules_frames = read(HERE / "rules-frames.json")
        self.frames = types.ModuleType("_fixed_fragment_frames")
        frame_bytes = (HERE / "frame_rules.py").read_bytes()
        assert sha(frame_bytes) == self.rules_frames["source_sha256"]
        exec(compile(frame_bytes, str(HERE / "frame_rules.py"), "exec"), self.frames.__dict__)
        self.source_bytes, self.source_hashes = {}, {}
        for rel, expected in BLOBS.items():
            data = (source_root / rel).read_bytes()
            if blob(data) != expected:
                raise RuntimeError("official source blob mismatch: " + rel)
            self.source_bytes[rel] = data
            self.source_hashes[rel] = {"git_blob": expected, "sha256": sha(data)}
        self.ledger_path = output / "attempt-ledger.json"
        self.ledger = read(self.ledger_path, {"attempts": [], "counters": {}, "case_consumption": {}})
        self.counters = Counter(self.ledger["counters"])
        self.phase, self.current = "unassigned", None
        package_name = "_fixed_fragment_official"
        package = types.ModuleType(package_name)
        package.__path__ = [str(source_root / "competition/tools/verifier")]
        sys.modules[package_name] = package
        loaded = {}
        for name in ("canon", "core", "stable_core"):
            module = types.ModuleType(package_name + "." + name)
            module.__file__ = str(source_root / "competition/tools/verifier" / (name + ".py"))
            module.__package__ = package_name
            sys.modules[module.__name__] = module
            setattr(package, name, module)
            exec(compile(self.source_bytes["competition/tools/verifier/" + name + ".py"], module.__file__, "exec"), module.__dict__)
            loaded[name] = module
        self.stable = loaded["stable_core"]
        self.original_apply = self.stable.apply_move

        def counted_apply(state, move):
            kind = "verification" if self.phase.endswith("verification") else "search"
            used = sum(v for k, v in self.counters.items() if k.endswith(kind + "_apply"))
            if used >= self.config[kind + "_official_apply_cap"]:
                raise SearchStopped("global_" + kind + "_official_apply_cap")
            if kind == "search":
                if self.current is not None and self.current["search_apply_calls"] >= self.current["remaining_search_budget"]:
                    raise SearchStopped("per_case_search_apply_cap")
                if self.current is None and self.counters["diagnostic_search_apply"] >= self.config["diagnostic_search_apply_cap"]:
                    raise SearchStopped("diagnostic_search_apply_cap")
            self.counters[self.phase + "_apply"] += 1
            if self.current is not None:
                self.current[kind + "_apply_calls"] += 1
            return self.original_apply(state, move)

        self.stable.apply_move = counted_apply
        self.inv = {r["relator"]: r["id"] for r in self.stable.MOVE_TABLE if r["category"] == "inversion"}
        self.mul = {(r["relator"], r["other"], r["invert_other"]): r["id"] for r in self.stable.MOVE_TABLE if r["category"] == "multiplication"}
        self.conj = {(r["relator"], r["conjugator"]): r["id"] for r in self.stable.MOVE_TABLE if r["category"] == "conjugation"}
        assert self.stable.MAX_RANK == self.config["official_max_rank"]

    def save(self):
        self.ledger["counters"] = dict(self.counters)
        dump(self.ledger_path, self.ledger)

    @contextmanager
    def attempt(self, command):
        entry = {"command": command, "started": now(), "locks": self.locks(), "before": dict(self.counters)}
        self.ledger["attempts"].append(entry)
        self.save()
        try:
            yield
            entry["status"] = "completed"
        except BaseException as exc:
            entry.update(status="failed", exception=type(exc).__name__, detail=str(exc), traceback=traceback.format_exc())
            raise
        finally:
            entry.update(finished=now(), after=dict(self.counters), consumed=dict(self.counters - Counter(entry["before"])))
            self.save()

    def locks(self):
        files = ("run_experiment.py", "config.json", "rules-symbolic.json", "rules-frames.json", "frame_rules.py")
        return {name: sha((HERE / name).read_bytes()) if (HERE / name).exists() else None for name in files}

    def verify(self, challenge, moves):
        previous = self.phase
        self.phase = previous.split("_")[0] + "_verification"
        self.counters[self.phase + "_calls"] += 1
        try:
            return self.stable.verify(challenge, list(moves), self.stable.MOVE_SPEC_VERSION, self.config["limits"])
        finally:
            self.phase = previous


def left_route(rt, i, j, sign):
    return (rt.inv[i], rt.mul[i, j, sign == 1], rt.inv[i])


def donor_route(rt, i, j, sign, h):
    mid = (rt.inv[i], rt.mul[i, j, sign == 1], rt.inv[i], rt.mul[i, j, sign == 1])
    return tuple(rt.conj[i, -a] for a in h) + mid + tuple(rt.conj[i, a] for a in reversed(h))


def h_words(rank, length):
    letters = tuple(a for g in range(1, rank + 1) for a in (g, -g))
    for word in itertools.product(letters, repeat=length):
        if all(word[t] != -word[t - 1] for t in range(1, length)):
            yield word


def frame_routes(rt, states, moves, stats):
    """Use the exact peer enumerator, counting its word reductions separately."""
    original_reduce = rt.frames.reduce_word
    def counted_reduce(word):
        word = tuple(word)
        stats["frame_word_reductions"] += 1
        stats["frame_reduction_letter_visits"] += len(word)
        return original_reduce(word)
    rt.frames.reduce_word = counted_reduce
    try:
        rows = list(rt.frames.frame_candidates(moves, states, rt.stable.MOVE_TABLE))
    finally:
        rt.frames.reduce_word = original_reduce
    stats["frame_candidate_routes"] = len(rows)
    for row in rows:
        yield row["start"], row["route"], {"family": "common_conjugation_frames", "expected_end": row["end"],
              "h": row["left_word"], "g": row["right_word"], "middle": [row["left_end"], row["right_start"]]}


def build_graph(rt, challenge, moves, result):
    states = [tuple(tuple(w) for w in challenge["initial_relators"])]
    for move in moves:
        state, reason = rt.stable.apply_move(states[-1], move)
        if reason:
            raise RuntimeError("original replay inapplicable: " + reason)
        states.append(state)
    lengths, n = list(map(size, states)), len(moves)
    state_index = defaultdict(list)
    for i, state in enumerate(states):
        state_index[state].append(i)
    edges, lookup = [], {}
    stats = {"routes_started": 0, "routes_completed": 0, "inapplicable": {}, "local_peak_rejections": 0,
             "exact_endpoint_matches": 0, "duplicate_sources": 0, "family_routes_started": {},
             "frame_word_reductions": 0, "frame_reduction_letter_visits": 0,
             "frame_candidate_routes": 0, "symbolic_rule_substring_tests": 0,
             "truncations": [], "library_exhausted": True}

    def add(i, j, route, route_lengths, source):
        key = (i, j, tuple(route))
        if key in lookup:
            edge = edges[lookup[key]]
            if source not in edge["sources"]:
                edge["sources"].append(source)
                stats["duplicate_sources"] += 1
            return
        if len(edges) >= rt.config["graph_edge_cap"]:
            raise SearchStopped("graph_edge_cap")
        edge = {"id": len(edges), "i": i, "j": j, "route": list(route), "length": len(route),
                "work": sum(route_lengths), "peak": max([lengths[i]] + route_lengths), "sources": [source]}
        lookup[key] = edge["id"]
        edges.append(edge)

    # Every original adjacent edge is retained before bounded generation.
    for i, move in enumerate(moves):
        add(i, i + 1, (move,), [lengths[i + 1]], {"family": "original_adjacent"})
    for i, state in enumerate(states[:-1]):
        for j in state_index[state]:
            if j > i:
                add(i, j, (), [], {"family": "exact_state_loop"})

    def routes():
        for rule in rt.symbolic["rules"]:
            old = rule["old_moves"]
            for i in range(n - len(old) + 1):
                stats["symbolic_rule_substring_tests"] += 1
                if moves[i:i + len(old)] == old and all(len(states[t]) == 2 for t in range(i, i + len(old) + 1)):
                    yield i, tuple(rule["new_moves"]), {"family": "symbolic_rules", "rule": rule["id"], "expected_end": i + len(old)}
        yield from frame_routes(rt, states, moves, stats)
        for i in range(n):
            for move in range(rt.stable.NUM_MOVES):
                yield i, (move,), {"family": "primitive", "move": move}
        for i in range(n):
            rank = len(states[i])
            for target in range(rank):
                for donor in range(rank):
                    if target != donor:
                        for sign in (1, -1):
                            yield i, left_route(rt, target, donor, sign), {"family": "left3", "target": target, "donor": donor, "sign": sign}
        for hlength in range(rt.config["h_max_length"] + 1):
            for i in range(n):
                rank = len(states[i])
                for h in h_words(rank, hlength):
                    for target in range(rank):
                        for donor in range(rank):
                            if target != donor:
                                for sign in (1, -1):
                                    source = {"family": "donor4" if not h else "h_donor", "target": target, "donor": donor, "sign": sign, "h": h}
                                    yield i, donor_route(rt, target, donor, sign, h), source

    try:
        for i, route, source in routes():
            stats["routes_started"] += 1
            family = source["family"]
            stats["family_routes_started"][family] = stats["family_routes_started"].get(family, 0) + 1
            state, route_lengths = states[i], []
            for move in route:
                state, reason = rt.stable.apply_move(state, move)
                if reason:
                    stats["inapplicable"][reason] = stats["inapplicable"].get(reason, 0) + 1
                    break
                length = size(state)
                route_lengths.append(length)
                if length > rt.config["limits"]["max_total_relator_length"]:
                    stats["local_peak_rejections"] += 1
                    break
            else:
                stats["routes_completed"] += 1
                if "expected_end" in source and state != states[source["expected_end"]]:
                    raise AssertionError("external rule did not preserve exact endpoint: " + repr(source))
                for j in state_index.get(state, ()):
                    if j > i:
                        stats["exact_endpoint_matches"] += 1
                        add(i, j, route, route_lengths, source)
    except SearchStopped as exc:
        stats["library_exhausted"] = False
        stats["truncations"].append(str(exc))
    graph = {"n": n, "initial_length": lengths[0], "states": states, "state_lengths": lengths, "edges": edges, "stats": stats}
    graph["graph_sha256"] = jsha(graph)
    result["graph"] = {"sha256": graph["graph_sha256"], "vertices": n + 1, "edges": len(edges), "stats": stats}
    return graph


def metrics(graph, path):
    selected = [graph["edges"][eid] for eid in path]
    return (sum(e["length"] for e in selected), graph["initial_length"] + sum(e["work"] for e in selected),
            max([graph["initial_length"]] + [e["peak"] for e in selected]))


def feasible(cost, limits):
    return cost[0] <= limits["max_path_length"] and cost[1] <= limits["max_work"] and cost[2] <= limits["max_total_relator_length"]


def expand(graph, path):
    return [move for eid in path for move in graph["edges"][eid]["route"]]


def greedy(graph, limits):
    path = list(range(graph["n"]))
    history = []
    while True:
        cost = metrics(graph, path)
        vertices = [0] + [graph["edges"][eid]["j"] for eid in path]
        positions = {v: t for t, v in enumerate(vertices)}
        best = None
        for edge in graph["edges"]:
            if edge["i"] not in positions or edge["j"] not in positions:
                continue
            a, b = positions[edge["i"]], positions[edge["j"]]
            candidate = path[:a] + [edge["id"]] + path[b:]
            newcost = metrics(graph, candidate)
            if newcost[0] >= cost[0] or not feasible(newcost, limits):
                continue
            key = newcost + (edge["i"], edge["j"], tuple(edge["route"]))
            if best is None or key < best[0]:
                best = (key, candidate, edge["id"], newcost)
        if best is None:
            return {"edge_path": path, "metrics": cost, "history": history, "graph_sha256": graph["graph_sha256"]}
        _, path, eid, newcost = best
        history.append({"edge": eid, "before": cost, "after": newcost})


def pareto_dp(graph, limits, config):
    labels = [[] for _ in range(graph["n"] + 1)]
    labels[0] = [{"cost": (0, graph["initial_length"], graph["initial_length"]), "path": ()}]
    outgoing = defaultdict(list)
    for edge in graph["edges"]:
        outgoing[edge["i"]].append(edge)
    stats = {"transitions": 0, "budget_rejected": 0, "dominated_rejected": 0, "accepted_labels": 1,
             "dominated_removed": 0, "peak_labels_at_vertex": 1, "truncations": [], "cap_discarded": 0}
    stop = False
    for i in range(graph["n"]):
        for label in labels[i]:
            for edge in outgoing[i]:
                if stats["transitions"] >= config["pareto_transitions_cap"]:
                    stats["truncations"].append("pareto_transitions_cap")
                    stop = True
                    break
                stats["transitions"] += 1
                old = label["cost"]
                cost = (old[0] + edge["length"], old[1] + edge["work"], max(old[2], edge["peak"]))
                if not feasible(cost, limits):
                    stats["budget_rejected"] += 1
                    continue
                target = labels[edge["j"]]
                if any(all(a <= b for a, b in zip(other["cost"], cost)) for other in target):
                    stats["dominated_rejected"] += 1
                    continue
                kept = [other for other in target if not all(a <= b for a, b in zip(cost, other["cost"]))]
                stats["dominated_removed"] += len(target) - len(kept)
                kept.append({"cost": cost, "path": label["path"] + (edge["id"],)})
                stats["accepted_labels"] += 1
                if len(kept) > config["pareto_labels_per_vertex_cap"]:
                    kept.sort(key=lambda x: x["cost"])
                    stats["cap_discarded"] += len(kept) - config["pareto_labels_per_vertex_cap"]
                    kept = kept[:config["pareto_labels_per_vertex_cap"]]
                    if "pareto_labels_per_vertex_cap" not in stats["truncations"]:
                        stats["truncations"].append("pareto_labels_per_vertex_cap")
                labels[edge["j"]] = kept
                stats["peak_labels_at_vertex"] = max(stats["peak_labels_at_vertex"], len(kept))
            if stop:
                break
        if stop:
            break
    stats["labels_per_vertex"] = list(map(len, labels))
    stats["terminal_pareto_metrics"] = sorted(label["cost"] for label in labels[-1])
    if not labels[-1]:
        stats["truncations"].append("no_terminal_label_fallback_original")
        path = list(range(graph["n"]))
    else:
        path = list(min(labels[-1], key=lambda x: x["cost"])["path"])
    return {"edge_path": path, "metrics": metrics(graph, path), "stats": stats,
            "graph_sha256": graph["graph_sha256"], "optimal_in_generated_graph": not stats["truncations"]}


def records_for(rt, ids):
    allowed = set(ids)
    assert not allowed.intersection(rt.protocol["excluded_reserved_v1_evaluation_ids"])
    # JSON decoding materializes public arrays; only allowed records are indexed.
    data = json.loads(rt.source_bytes["competition/examples/stable_training_424.json"])
    chosen = {r["training_id"]: r for r in data["instances"] if r["training_id"] in allowed}
    assert set(chosen) == allowed
    manifest = json.loads(rt.source_bytes["competition/examples/training_manifest.json"])
    official = {c["challenge_id"]: c for c in manifest["challenges"]}
    records = []
    for ident in ids:
        record = chosen[ident]
        challenge = dict(official[ident.replace("ms-train-", "sac-train-")])
        for field in ("initial_relators", "target_relators", "move_spec_version"):
            assert record[field] == challenge[field]
        challenge["source_training_id"] = ident
        records.append((challenge, list(record["moves"])))
    return records


def run_case(rt, challenge, moves, group):
    ident = challenge.get("source_training_id", challenge["challenge_id"])
    key = group + ":" + ident
    prior = rt.ledger["case_consumption"].get(key, 0)
    result = {"id": ident, "challenge": challenge, "group": group, "original_moves": moves,
              "locks": rt.locks(), "search_apply_calls": 0, "verification_apply_calls": 0,
              "prior_search_consumption": prior, "remaining_search_budget": max(0, rt.config["search_apply_cap_per_case"] - prior),
              "status": "running"}
    rt.current, rt.phase = result, group + "_search"
    started = time.monotonic()
    try:
        result["original_verdict"] = rt.verify(challenge, moves)
        assert result["original_verdict"]["ok"]
        graph = build_graph(rt, challenge, moves, result)
        graph_path = rt.output / "graphs" / (ident + ".json")
        dump(graph_path, graph)
        result["graph"]["file"] = str(graph_path.relative_to(rt.output))
        for name, selection in (("greedy", greedy(graph, rt.config["limits"])),
                                ("dp", pareto_dp(graph, rt.config["limits"], rt.config))):
            selection["moves"] = expand(graph, selection["edge_path"])
            selection["official_verdict"] = rt.verify(challenge, selection["moves"])
            verdict = selection["official_verdict"]
            assert verdict["ok"], (name, verdict)
            assert tuple(selection["metrics"]) == (verdict["length"], verdict["work"], verdict["peak_total_relator_length"])
            selection["selected_sources"] = [graph["edges"][eid]["sources"] for eid in selection["edge_path"]]
            result[name] = selection
        assert result["greedy"]["graph_sha256"] == result["dp"]["graph_sha256"] == graph["graph_sha256"]
        if result["dp"]["optimal_in_generated_graph"]:
            assert tuple(result["dp"]["metrics"]) <= tuple(result["greedy"]["metrics"])
        result["status"] = "completed"
    except BaseException as exc:
        result.update(status="failed", exception=type(exc).__name__, detail=str(exc), traceback=traceback.format_exc())
        raise
    finally:
        result["wall_seconds"] = time.monotonic() - started
        rt.ledger["case_consumption"][key] = prior + result["search_apply_calls"]
        result["cumulative_search_apply_calls"] = rt.ledger["case_consumption"][key]
        rt.current = None
        rt.save()
        path = rt.output / (group + "-results.json")
        data = read(path, [])
        data.append(result)
        dump(path, data)
    print(json.dumps({"group": group, "id": ident, "original": len(moves), "greedy": result["greedy"]["metrics"],
                      "dp": result["dp"]["metrics"], "edges": result["graph"]["edges"], "apply": result["search_apply_calls"],
                      "truncations": result["graph"]["stats"]["truncations"]}), flush=True)
    return result


def selfcheck(rt):
    rt.phase = "diagnostic_search"
    checks = []
    for rank in (2, 3):
        state = ((1, 2, 1), (2, -1, 2)) + (((3, 1, -3),) if rank == 3 else ())
        for target in range(rank):
            for donor in range(rank):
                if target == donor:
                    continue
                for sign in (1, -1):
                    for h in ((), (1,), (1, -2)):
                        v = state[donor] if sign == 1 else inverse(state[donor])
                        w = reduce_word(h + v + inverse(h))
                        expected = list(state)
                        expected[target] = reduce_word(w + state[target] + inverse(w))
                        route = donor_route(rt, target, donor, sign, h)
                        observed = state
                        for move in route:
                            observed, reason = rt.stable.apply_move(observed, move)
                            assert reason is None
                        assert observed == tuple(expected)
                        checks.append({"rank": rank, "target": target, "donor": donor, "sign": sign, "h": h})
    # The published overlap counterexample isolates selector behavior only.
    edges = [{"id": i, "i": i, "j": i + 1, "route": [i], "length": 1, "work": 1, "peak": 1} for i in range(7)]
    for i, j, length in ((0, 6, 2), (0, 3, 1), (3, 7, 1)):
        edges.append({"id": len(edges), "i": i, "j": j, "route": [0] * length, "length": length, "work": length, "peak": 1})
    graph = {"n": 7, "initial_length": 1, "edges": edges, "graph_sha256": "synthetic-selector-only"}
    g, d = greedy(graph, rt.config["limits"]), pareto_dp(graph, rt.config["limits"], rt.config)
    assert g["metrics"][0] == 3 and d["metrics"][0] == 2
    # A short expensive prefix cannot replace a longer cheap prefix under work budget.
    trap_edges = [dict(id=0, i=0, j=1, route=[0], length=1, work=5, peak=4),
                  dict(id=1, i=0, j=1, route=[0, 0], length=2, work=2, peak=2),
                  dict(id=2, i=1, j=2, route=[0], length=1, work=4, peak=2)]
    trap = {"n": 2, "initial_length": 1, "edges": trap_edges, "graph_sha256": "synthetic-resource-trap-only"}
    tight = dict(rt.config["limits"], max_work=8)
    t = pareto_dp(trap, tight, rt.config)
    assert tuple(t["metrics"]) == (3, 7, 2) and t["stats"]["labels_per_vertex"][1] == 2
    # Compare the algorithm against exhaustive fixed-DAG paths with three budgets.
    exhaustive = []
    for workcap in (4, 6, 20):
        limits = dict(rt.config["limits"], max_work=workcap)
        allpaths = []
        def walk(i, path):
            if i == graph["n"]:
                cost = metrics(graph, path)
                if feasible(cost, limits):
                    allpaths.append(cost)
                return
            for edge in graph["edges"]:
                if edge["i"] == i:
                    walk(edge["j"], path + [edge["id"]])
        walk(0, [])
        got = pareto_dp(graph, limits, rt.config)
        assert tuple(got["metrics"]) == min(allpaths)
        exhaustive.append({"work_cap": workcap, "paths": len(allpaths), "best": got["metrics"]})
    out = {"status": "passed", "identity_cases": len(checks), "identity_parameters": checks,
           "selector_overlap": {"greedy": g, "dp": d}, "resource_trap": t, "exhaustive_comparisons": exhaustive,
           "scope": "abstract graph selector fixtures are not official AC instances", "locks": rt.locks()}
    dump(rt.output / "selfcheck.json", out)


def development(rt):
    assert read(rt.output / "selfcheck.json")["status"] == "passed"
    assert not (rt.output / "FREEZE.json").exists(), "development is closed after freeze"
    records = records_for(rt, rt.protocol["known_development_training_ids"])
    manifest = json.loads(rt.source_bytes["competition/tools/verifier/data/manifest.json"])
    incumbent = rt.protocol["old_scored_incumbent"]
    challenge = next(c for c in manifest["challenges"] if c["challenge_id"] == incumbent["id"])
    records.append((challenge, incumbent["moves"]))
    done = {r["id"] for r in read(rt.output / "development-results.json", []) if r["status"] == "completed"}
    for challenge, moves in records:
        if challenge.get("source_training_id", challenge["challenge_id"]) not in done:
            run_case(rt, challenge, moves, "development")


def freeze(rt):
    path = rt.output / "FREEZE.json"
    if path.exists():
        raise RuntimeError("freeze already exists")
    results = read(rt.output / "development-results.json", [])
    assert len([r for r in results if r["status"] == "completed"]) == 21
    assert rt.rules_frames is not None, "frame rule hash must be fixed before freeze"
    assert all(r["locks"] == rt.locks() for r in results if r["status"] == "completed"), "code/config/rules changed after development; explicit revalidation needed"
    out = {"frozen_at": now(), "locks": rt.locks(), "config": rt.config, "source_hashes": rt.source_hashes,
           "protocol_sha256": sha((HERE.parent / "PROTOCOL.json").read_bytes()),
           "selected_test_metadata": rt.protocol["new_public_training_test"],
           "selected_test_metadata_sha256": jsha(rt.protocol["new_public_training_test"]),
           "development_results_sha256": sha((rt.output / "development-results.json").read_bytes()),
           "counter_snapshot": dict(rt.counters), "new_test_move_arrays_indexed": False,
           "excluded_v1_move_arrays_indexed": False, "optimality_scope": "generated fixed original-state DAG only"}
    dump(path, out)


def test(rt):
    frozen = read(rt.output / "FREEZE.json")
    assert frozen and frozen["locks"] == rt.locks(), "freeze/code/config/rules mismatch"
    assert frozen["source_hashes"] == rt.source_hashes
    assert frozen["protocol_sha256"] == sha((HERE.parent / "PROTOCOL.json").read_bytes())
    path = rt.output / "TEST-ACCESS.json"
    if not path.exists():
        dump(path, {"first_action_access_not_before": now(), "freeze_sha256": sha((rt.output / "FREEZE.json").read_bytes()),
                    "locks": rt.locks(), "selected_ids": [r["id"] for r in frozen["selected_test_metadata"]],
                    "boundary": "written after freeze checks and before records_for indexes selected move arrays", "tuning_allowed": False})
    ids = [r["id"] for r in frozen["selected_test_metadata"]]
    done = {r["id"] for r in read(rt.output / "test-results.json", []) if r["status"] == "completed"}
    for challenge, moves in records_for(rt, ids):
        if challenge["source_training_id"] not in done:
            run_case(rt, challenge, moves, "test")


def report(rt):
    cases = read(rt.output / "development-results.json", []) + read(rt.output / "test-results.json", [])
    rows = []
    for r in cases:
        if r["status"] != "completed":
            continue
        v = r["original_verdict"]
        rows.append({"id": r["id"], "group": r["group"], "original": [v["length"], v["work"], v["peak_total_relator_length"]],
                     "greedy": r["greedy"]["metrics"], "dp": r["dp"]["metrics"], "edges": r["graph"]["edges"],
                     "search_apply": r["search_apply_calls"], "verification_apply": r["verification_apply_calls"],
                     "graph_truncations": r["graph"]["stats"]["truncations"], "dp_truncations": r["dp"]["stats"]["truncations"],
                     "pareto_accepted": r["dp"]["stats"]["accepted_labels"], "pareto_terminal": len(r["dp"]["stats"]["terminal_pareto_metrics"]),
                     "dp_length_better_than_greedy": r["dp"]["metrics"][0] < r["greedy"]["metrics"][0],
                     "dp_lex_better_than_greedy": tuple(r["dp"]["metrics"]) < tuple(r["greedy"]["metrics"]),
                     "dp_shortened_original": r["dp"]["metrics"][0] < v["length"]})
    out = {"created": now(), "cases": rows, "complete_cases": len(rows), "failed_case_attempts": sum(r["status"] != "completed" for r in cases),
           "counters": dict(rt.counters), "budget": rt.config["case_allocation"],
           "dp_length_wins_over_greedy": sum(r["dp_length_better_than_greedy"] for r in rows),
           "dp_lex_wins_over_greedy": sum(r["dp_lex_better_than_greedy"] for r in rows),
           "dp_shortens_original": sum(r["dp_shortened_original"] for r in rows),
           "graph_truncated_cases": sum(bool(r["graph_truncations"]) for r in rows),
           "dp_truncated_cases": sum(bool(r["dp_truncations"]) for r in rows),
           "all_selected_certificates_accepted_from_original_initial_state": all(r[arm]["official_verdict"]["ok"] for r in cases if r["status"] == "completed" for arm in ("greedy", "dp")),
           "locks": rt.locks(), "excluded_v1_move_arrays_indexed": False, "native_yohaku_connected": False}
    dump(rt.output / "results.json", out)
    print(json.dumps({k: out[k] for k in ("complete_cases", "dp_length_wins_over_greedy", "dp_lex_wins_over_greedy", "dp_shortens_original", "graph_truncated_cases", "dp_truncated_cases", "counters")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("selfcheck", "development", "freeze", "test", "report"))
    parser.add_argument("--official-root", type=Path, default=HERE.parent.parent / "ac_official")
    parser.add_argument("--output", type=Path, default=HERE)
    args = parser.parse_args()
    rt = Runtime(args.official_root.resolve(), args.output.resolve())
    with rt.attempt(args.command):
        globals()[args.command](rt)


if __name__ == "__main__":
    main()
