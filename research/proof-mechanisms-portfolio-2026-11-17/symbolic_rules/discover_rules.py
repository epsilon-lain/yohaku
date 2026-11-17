#!/usr/bin/env python3
"""Finite universal rank-two rewrite discovery; Python standard library only.

One symbolic operation = one application of one I/M/C primitive to an
ordered pair of freely reduced words, including all inversions/reductions
needed by that primitive. Dictionary lookup, hashing and path comparison
are not action applications and are reported separately where useful.
"""
import argparse
import hashlib
import itertools
import json
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
INITIAL = ((3,), (4,))  # 1=X, 2=Y, 3=U, 4=V: four independent generators.
INVERSE = (0, 1, 3, 2, 5, 4, 7, 6, 9, 8, 11, 10, 13, 12)
OPERATION_CAP = 200000
SHORT_MAX = 3
OLD_MAX = 6


def reduce_word(word):
    stack = []
    for a in word:
        if stack and stack[-1] == -a:
            stack.pop()
        else:
            stack.append(a)
    return tuple(stack)


def invert(word):
    return tuple(-a for a in reversed(word))


class Model:
    def __init__(self):
        self.counts = Counter()

    def apply(self, state, move, phase):
        self.counts[phase] += 1
        if sum(self.counts.values()) > OPERATION_CAP:
            raise RuntimeError("symbolic operation budget exhausted")
        u, v = state
        if move == 0:
            return invert(u), v
        if move == 1:
            return u, invert(v)
        if move == 2:
            return reduce_word(u + v), v
        if move == 3:
            return reduce_word(u + invert(v)), v
        if move == 4:
            return u, reduce_word(v + u)
        if move == 5:
            return u, reduce_word(v + invert(u))
        if 6 <= move <= 9:
            g = (1, -1, 2, -2)[move - 6]
            return reduce_word((g,) + u + (-g,)), v
        if 10 <= move <= 13:
            g = (1, -1, 2, -2)[move - 10]
            return u, reduce_word((g,) + v + (-g,))
        raise ValueError(move)

    def replay(self, moves, phase):
        state = INITIAL
        states = [state]
        for move in moves:
            state = self.apply(state, move, phase)
            states.append(state)
        return states


def cancel_adjacent_inverses(moves):
    stack = []
    for move in moves:
        if stack and INVERSE[stack[-1]] == move:
            stack.pop()
        else:
            stack.append(move)
    return tuple(stack)


def rank_before(moves, rank=2):
    ranks = []
    for move in moves:
        ranks.append(rank)
        if move == 14:
            rank += 1
        elif 15 <= move <= 22:
            rank -= 1
    return ranks


def enumerate_short(model):
    """All 2955 strings of length <= 3, using prefix reuse (2954 ops)."""
    table = {INITIAL: ()}
    alternatives = defaultdict(list)
    alternatives[INITIAL].append(())
    layer = [((), INITIAL)]
    string_counts = {0: 1}
    for depth in range(1, SHORT_MAX + 1):
        next_layer = []
        for prefix, state in layer:
            for move in range(14):
                path = prefix + (move,)
                output = model.apply(state, move, "enumerate_short")
                next_layer.append((path, output))
                if output not in table:
                    table[output] = path
                if len(path) == len(table[output]):
                    alternatives[output].append(path)
        string_counts[depth] = len(next_layer)
        layer = next_layer
    return table, alternatives, string_counts


def scan_development(model, records, table):
    hits = defaultdict(list)
    scanned = Counter()
    for record in records:
        moves = record["moves"]
        ranks = rank_before(moves)
        for start in range(len(moves)):
            if ranks[start] != 2 or not 0 <= moves[start] < 14:
                continue
            state = INITIAL
            old = ()
            for end in range(start + 1, min(len(moves), start + OLD_MAX) + 1):
                move = moves[end - 1]
                if ranks[end - 1] != 2 or not 0 <= move < 14:
                    break
                old += (move,)
                state = model.apply(state, move, "scan_development")
                scanned[len(old)] += 1
                new = table.get(state)
                if new is not None and len(new) < len(old):
                    hits[(old, new, state)].append({
                        "training_id": record["training_id"],
                        "start": start, "end_exclusive": end,
                    })
    return hits, scanned


def signature_json(signature):
    return [list(word) for word in signature]


def run():
    inp = json.loads((HERE / "DEVELOPMENT-INPUT.json").read_text())
    protocol = json.loads((HERE.parent / "PROTOCOL.json").read_text())
    allowed = set(protocol["known_development_training_ids"])
    assert set(inp["accessed_action_ids"]) == allowed
    assert {r["training_id"] for r in inp["records"]} == allowed
    model = Model()
    table, alternatives, string_counts = enumerate_short(model)
    hits, scanned = scan_development(model, inp["records"], table)
    selected, excluded = [], []
    for (old, new, signature), sources in sorted(hits.items()):
        if signature == INITIAL:
            category = "identity_output"
        elif cancel_adjacent_inverses(old) == new:
            category = "adjacent_inverse_cancellation"
        else:
            category = "nontrivial_universal_rewrite"
        entry = {
            "old_moves": list(old), "new_moves": list(new),
            "old_length": len(old), "new_length": len(new),
            "length_saved": len(old) - len(new),
            "classification": category,
            "proof_symbolic_output": signature_json(signature),
            "sources": sources,
        }
        if category == "nontrivial_universal_rewrite":
            old_states = model.replay(old, "selected_proof_replay")
            new_states = model.replay(new, "selected_proof_replay")
            assert old_states[-1] == new_states[-1] == signature
            entry["proof_old_symbolic_states"] = [signature_json(s) for s in old_states]
            entry["proof_new_symbolic_states"] = [signature_json(s) for s in new_states]
            entry["shortest_known_alternatives"] = [list(p) for p in alternatives[signature]]
            entry["conditions"] = {
                "rank": 2,
                "alphabet": "ambient X,Y; arbitrary freely reduced U,V in F(X,Y)",
                "endpoint": "complete ordered freely reduced tuple equal; no quotient equivalence",
                "resource_guard": "Replay replacement on actual entry and complete resulting certificate from original initial state; require official limits.",
                "limits": {"max_path_length": 100000, "max_total_relator_length": 10000, "max_work": 5000000},
            }
            selected.append(entry)
        else:
            excluded.append(entry)
    for index, entry in enumerate(selected, 1):
        entry["id"] = "sym-dev-%03d" % index
    result = {
        "version": "symbolic-rank2-dev-v1",
        "frozen": True,
        "official_commit": protocol["official_commit"],
        "symbol_encoding": {"1": "X", "2": "Y", "3": "U", "4": "V", "negative": "inverse"},
        "initial_symbolic_state": signature_json(INITIAL),
        "proof": "In F(X,Y,U,V), equality of reduced ordered outputs implies equality after every homomorphism fixing X,Y and substituting arbitrary U,V in F(X,Y). Each I/M/C primitive commutes with that substitution.",
        "interface": "At any rank2 occurrence of old_moves, expand new_moves verbatim; verify the complete certificate and resources. No state parameters, no official search.",
        "selection": {"short_max": SHORT_MAX, "old_max": OLD_MAX, "development_ids": sorted(allowed), "test_actions_accessed": [], "tie_break": "minimum primitive length then lexicographic move list", "exclude": ["identity output", "adjacent inverse cancellation", "known four-step donor rule", "direct destabilization mechanism"]},
        "rules": selected,
    }
    def write(name, data):
        (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")
    write("RULES.json", result)
    write("EXCLUDED-CANDIDATES.json", excluded)
    summary = {
        "short_string_counts": string_counts,
        "short_total_strings": sum(string_counts.values()),
        "distinct_short_fingerprints": len(table),
        "scanned_fragment_counts_by_length": dict(sorted(scanned.items())),
        "scanned_fragment_occurrences": sum(scanned.values()),
        "unique_shortenable_old_new_pairs": len(hits),
        "selected_rule_count": len(selected),
        "selected_occurrence_count": sum(len(r["sources"]) for r in selected),
        "excluded_counts": dict(Counter(r["classification"] for r in excluded)),
        "symbolic_operations": dict(model.counts),
        "symbolic_operations_total": sum(model.counts.values()),
        "symbolic_operation_cap": OPERATION_CAP,
        "official_search_apply_calls": 0,
        "official_verification_apply_calls_in_discovery": 0,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "input_sha256": hashlib.sha256((HERE / "DEVELOPMENT-INPUT.json").read_bytes()).hexdigest(),
        "rules_sha256": hashlib.sha256((HERE / "RULES.json").read_bytes()).hexdigest(),
    }
    write("DISCOVERY-RESULTS.json", summary)
    print(json.dumps(summary, ensure_ascii=False))
    for entry in selected:
        print(entry["id"], entry["old_moves"], "->", entry["new_moves"], "occurrences", len(entry["sources"]))


if __name__ == "__main__":
    run()
