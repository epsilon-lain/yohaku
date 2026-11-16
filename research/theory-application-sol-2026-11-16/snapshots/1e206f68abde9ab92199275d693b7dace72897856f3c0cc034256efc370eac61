"""Exact, bounded checks for theory-white-points-v1; standard library only.

Full graph enumeration is independent of the component-partition theorem and
is performed for m=3,4. Larger m checks enumerate positive edge subsets of one
cycle and test the proved subset-sum criterion, not all candidate graphs.
Run without flags to write RESULTS.json; --check recomputes and compares it.
"""
from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations, permutations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VERSION = "theory-white-points-v1"


def edge_system(n):
    pairs = tuple(combinations(range(n), 2))
    return pairs, {edge: 1 << i for i, edge in enumerate(pairs)}


def cycle_mask(order, bits):
    return sum(bits[tuple(sorted((a, b)))]
               for a, b in zip(order, order[1:] + order[:1]))


def cycles_on(vertices, bits):
    vertices = tuple(sorted(vertices))
    anchor, rest = vertices[0], vertices[1:]
    for order in permutations(rest):
        # The minimum label anchors rotation; this removes reflection.
        if order[0] < order[-1]:
            yield cycle_mask((anchor,) + order, bits)


def enumerate_universe(m):
    n = 2 * m
    pairs, bits = edge_system(n)
    single = set(cycles_on(tuple(range(n)), bits))
    double = set()
    for tail in combinations(range(1, n), m - 1):
        first = (0,) + tail
        second = tuple(v for v in range(n) if v not in first)
        for left in cycles_on(first, bits):
            for right in cycles_on(second, bits):
                double.add(left | right)
    assert not (single & double)
    return pairs, bits, single, double


def edges_of(mask, pairs):
    return [list(edge) for i, edge in enumerate(pairs) if mask & (1 << i)]


def component_sizes(mask, n, pairs):
    adjacency = [[] for _ in range(n)]
    for i, (a, b) in enumerate(pairs):
        if mask & (1 << i):
            adjacency[a].append(b)
            adjacency[b].append(a)
    unseen = set(range(n))
    sizes = []
    while unseen:
        root = unseen.pop()
        stack = [root]
        size = 0
        while stack:
            v = stack.pop()
            size += 1
            for neighbor in adjacency[v]:
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    stack.append(neighbor)
        sizes.append(size)
    return tuple(sorted(sizes))


def subset_sum(values, target):
    reachable = 1
    for value in values:
        reachable |= reachable << value
    return bool(reachable & (1 << target))


def subsets_of_edges(target):
    support = [1 << i for i in range(target.bit_length()) if target & (1 << i)]
    for index_mask in range(1 << len(support)):
        mask = 0
        for i, edge_bit in enumerate(support):
            if index_mask & (1 << i):
                mask |= edge_bit
        yield mask


def intersection(values):
    result = values[0]
    for value in values[1:]:
        result &= value
    return result


def full_graph_check(m):
    n = 2 * m
    pairs, bits, single, double = enumerate_universe(m)
    universe = sorted(single | double)
    targets = {
        "single_cycle": cycle_mask(tuple(range(n)), bits),
        "two_cycles": cycle_mask(tuple(range(m)), bits)
        | cycle_mask(tuple(range(m, n)), bits),
    }
    results = {}
    for target_name, target in targets.items():
        target_type = single if target_name == "single_cycle" else double
        cert_iso = {}
        cert_label = {}
        candidate_count = {}
        closure = {}
        for observed in subsets_of_edges(target):
            candidates = [graph for graph in universe if graph & observed == observed]
            assert candidates and target in candidates
            cert_iso[observed] = all(graph in target_type for graph in candidates)
            cert_label[observed] = candidates == [target]
            candidate_count[observed] = len(candidates)
            closure[observed] = intersection(candidates)
            if target_name == "single_cycle" and observed != target:
                predicted = not subset_sum(component_sizes(observed, n, pairs), m)
                assert predicted == cert_iso[observed]
            if target_name == "two_cycles":
                first_cycle = cycle_mask(tuple(range(m)), bits)
                second_cycle = cycle_mask(tuple(range(m, n)), bits)
                predicted = (observed & first_cycle == first_cycle
                             or observed & second_cycle == second_cycle)
                assert predicted == cert_iso[observed]
        minimum_iso = min(mask.bit_count() for mask, yes in cert_iso.items() if yes)
        minimum_label = min(mask.bit_count() for mask, yes in cert_label.items() if yes)
        min_iso_sets = sorted(mask for mask, yes in cert_iso.items()
                              if yes and mask.bit_count() == minimum_iso)
        min_label_sets = sorted(mask for mask, yes in cert_label.items()
                                if yes and mask.bit_count() == minimum_label)
        inclusion_minimal = [mask for mask, yes in cert_iso.items() if yes
                             and all(not cert_iso[mask ^ (1 << i)]
                                     for i in range(mask.bit_length())
                                     if mask & (1 << i))]
        histogram = []
        for size in range(n + 1):
            masks = [mask for mask in cert_iso if mask.bit_count() == size]
            histogram.append({
                "observed_edges": size,
                "subsets": len(masks),
                "iso_certificates": sum(cert_iso[mask] for mask in masks),
                "label_certificates": sum(cert_label[mask] for mask in masks),
                "candidate_count_min": min(candidate_count[mask] for mask in masks),
                "candidate_count_max": max(candidate_count[mask] for mask in masks),
            })
        assert minimum_iso == m
        assert len(min_iso_sets) == ((n + 2 * (m % 2))
                                     if target_name == "single_cycle" else 2)
        assert minimum_label == (n - 2 if target_name == "single_cycle"
                                  else (m if m == 3 else n - 2))
        results[target_name] = {
            "minimum_iso_edges": minimum_iso,
            "minimum_label_edges": minimum_label,
            "minimum_iso_certificate_count": len(min_iso_sets),
            "minimum_label_certificate_count": len(min_label_sets),
            "minimum_iso_certificates": [edges_of(mask, pairs) for mask in min_iso_sets],
            "inclusion_minimal_iso_histogram": {
                str(size): count for size, count in sorted(
                    Counter(mask.bit_count() for mask in inclusion_minimal).items())
            },
            "histogram": histogram,
        }
        if m == 4 and target_name == "single_cycle":
            base = sum(bits[(i, i + 1)] for i in range(4))
            a, b = bits[(4, 5)], bits[(6, 7)]
            assert closure[base] == base
            assert not (closure[base] & b)
            assert closure[base | a] & b
            assert not (closure[base | b] & a)
            results["closure_exchange_counterexample"] = {
                "S": edges_of(base, pairs), "a": [4, 5], "b": [6, 7],
                "Cl_S": edges_of(closure[base], pairs),
                "Cl_S_a": edges_of(closure[base | a], pairs),
                "Cl_S_b": edges_of(closure[base | b], pairs),
                "candidate_counts": {
                    "S": candidate_count[base],
                    "S_plus_a": candidate_count[base | a],
                    "S_plus_b": candidate_count[base | b],
                },
                "witness_without_b": [0, 1, 2, 3, 4, 6, 5, 7],
                "witness_S_plus_b_without_a": [0, 1, 2, 3, 4, 6, 7, 5],
            }
            witness_1 = cycle_mask((0, 1, 2, 3, 4, 6, 5, 7), bits)
            witness_2 = cycle_mask((0, 1, 2, 3, 4, 6, 7, 5), bits)
            assert witness_1 in single and witness_1 & base == base and not witness_1 & b
            assert witness_2 in single and witness_2 & (base | b) == (base | b)
            assert not witness_2 & a
    return {
        "m": m, "n": n, "single_cycle_count": len(single),
        "two_cycle_count": len(double), "universe_count": len(universe),
        "check_method": "all candidate graphs; all subsets of each target's edges",
        "targets": results,
    }


def positive_partitions(total, length, least=1):
    if length == 0:
        if total == 0:
            yield ()
        return
    for first in range(least, total // length + 1):
        for rest in positive_partitions(total - first, length - 1, first):
            yield (first,) + rest


def check_integer_lemma(maximum_m=24):
    rows = []
    for m in range(3, maximum_m + 1):
        count, failures = 0, []
        for values in positive_partitions(2 * m, m):
            count += 1
            if not subset_sum(values, m):
                failures.append(values)
        expected = [(1,) * (m - 1) + (m + 1,)]
        if m % 2:
            expected.append((2,) * m)
        assert set(failures) == set(expected)
        # The >=m+1-part lemma is also checked independently at the boundary.
        more_parts = list(positive_partitions(2 * m, m + 1))
        assert all(subset_sum(values, m) for values in more_parts)
        rows.append({"m": m, "m_part_partitions_checked": count,
                     "m_plus_1_part_partitions_checked": len(more_parts),
                     "no_half_sum_partitions": [list(row) for row in failures]})
    return rows


def check_cycle_subsets(maximum_m=8):
    rows = []
    for m in range(3, maximum_m + 1):
        n = 2 * m
        # A cycle-specific implementation, independent of graph mask labels.
        minimum_patterns = []
        checked = 0
        for chosen in combinations(range(n), m):
            chosen = frozenset(chosen)
            parent = list(range(n))

            def find(v):
                while v != parent[v]:
                    parent[v] = parent[parent[v]]
                    v = parent[v]
                return v

            for edge in chosen:
                left, right = find(edge), find((edge + 1) % n)
                parent[left] = right
            sizes = Counter(find(v) for v in range(n)).values()
            no_half_sum = not subset_sum(sizes, m)
            consecutive = any(chosen == frozenset((start + offset) % n
                                                   for offset in range(m))
                              for start in range(n))
            perfect_matching = all(((v - 1) % n in chosen) + (v in chosen) == 1
                                   for v in range(n))
            predicted = consecutive or (m % 2 == 1 and perfect_matching)
            assert no_half_sum == predicted
            checked += 1
            if no_half_sum:
                minimum_patterns.append(sorted(chosen))
        assert len(minimum_patterns) == n + 2 * (m % 2)
        rows.append({"m": m, "edge_subsets_of_size_m_checked": checked,
                     "minimum_certificate_count": len(minimum_patterns),
                     "minimum_patterns_edge_indices": minimum_patterns})
    return rows


def build_results():
    return {
        "version": VERSION,
        "execution_surface": "ChatGPT Work shared workspace; not original Yohaku runtime",
        "cost": "unit cost for every independently established positive edge property",
        "scope": "m>=3; labeled simple 2-regular graphs on 2m vertices, girth>=m",
        "full_enumeration": [full_graph_check(m) for m in (3, 4)],
        "integer_lemma_finite_checks": check_integer_lemma(),
        "cycle_minimum_pattern_checks": check_cycle_subsets(),
        "limitations": [
            "General-m theorem is proved in README; finite checks do not replace it.",
            "For m>4 the program does not enumerate all candidate graphs.",
            "No Andrews-Curtis performance result follows from this graph model.",
            "No prior probability on labeled representations is assumed.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = build_results()
    destination = ROOT / "RESULTS.json"
    if args.check:
        assert json.loads(destination.read_text(encoding="utf-8")) == result
    else:
        destination.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n",
                               encoding="utf-8")
    print(json.dumps({
        "version": VERSION, "mode": "check" if args.check else "write",
        "full_enumeration": [{
            "m": row["m"], "universe_count": row["universe_count"],
            "targets": {name: {key: facts[key] for key in (
                "minimum_iso_edges", "minimum_label_edges",
                "minimum_iso_certificate_count", "inclusion_minimal_iso_histogram")}
                        for name, facts in row["targets"].items()
                        if name != "closure_exchange_counterexample"},
        } for row in result["full_enumeration"]],
        "integer_m_range": [3, 24], "cycle_pattern_m_range": [3, 8],
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
