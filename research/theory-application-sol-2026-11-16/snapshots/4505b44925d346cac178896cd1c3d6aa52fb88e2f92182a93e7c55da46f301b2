"""Independent exhaustive C8 / 2C4 positive-observation check.

Builds cycle edge sets directly from vertex permutations, without importing
theory-team code. Tracks completion counts for every realizable edge subset.
"""
from itertools import combinations, permutations
from pathlib import Path
import json


def cycles(vertices):
    first, *tail = sorted(vertices)
    for order in permutations(tail):
        if order[0] > order[-1]:
            continue
        walk = (first,) + order
        yield frozenset(tuple(sorted((walk[i], walk[(i + 1) % len(walk)])))
                        for i in range(len(walk)))


def run():
    edges = list(combinations(range(8), 2))
    index = {e: i for i, e in enumerate(edges)}
    def mask(edge_set):
        return sum(1 << index[e] for e in edge_set)
    graph_classes = [set(mask(c) for c in cycles(range(8))), set()]
    for rest in combinations(range(1, 8), 3):
        left = {0, *rest}
        right = set(range(8)) - left
        for a in cycles(left):
            for b in cycles(right):
                graph_classes[1].add(mask(a | b))
    completions = {}
    for kind, graphs in enumerate(graph_classes):
        for graph in graphs:
            subset = graph
            while True:
                row = completions.setdefault(subset, [0, 0])
                row[kind] += 1
                if subset == 0:
                    break
                subset = (subset - 1) & graph
    patterns = [0] * 9
    type_identifying = [[0] * 9 for _ in range(2)]
    exact_identifying = [[0] * 9 for _ in range(2)]
    for subset, counts in completions.items():
        k = subset.bit_count()
        patterns[k] += 1
        for kind in range(2):
            if counts[kind] and not counts[1 - kind]:
                type_identifying[kind][k] += 1
                if counts[kind] == 1:
                    exact_identifying[kind][k] += 1
    result = {
        'scope': 'all realizable positive edge subsets in labelled C8 or 2C4',
        'graph_counts_C8_2C4': [len(g) for g in graph_classes],
        'observation_patterns_by_edge_count': patterns,
        'type_identifying_by_edge_count_C8_2C4': type_identifying,
        'exact_identifying_by_edge_count_C8_2C4': exact_identifying,
        'minimum_type_identifying_C8_2C4': [next(i for i,v in enumerate(row) if v) for row in type_identifying],
        'minimum_exact_identifying_C8_2C4': [next(i for i,v in enumerate(row) if v) for row in exact_identifying],
    }
    # Inspect the exchange counterexample using the independently built universe.
    def edge_mask(items):
        return mask(frozenset(tuple(sorted(e)) for e in items))
    universe = graph_classes[0] | graph_classes[1]
    base = edge_mask([(0,1),(1,2),(2,3),(3,4)])
    a, b = edge_mask([(4,5)]), edge_mask([(6,7)])
    audit = {}
    for name, observed in [('S',base),('S_plus_a',base|a),('S_plus_b',base|b),('S_plus_a_plus_b',base|a|b)]:
        candidates = [g for g in universe if g & observed == observed]
        assert candidates
        closure = candidates[0]
        for graph in candidates[1:]:
            closure &= graph
        audit[name] = {'candidate_count':len(candidates),
                       'closure_edges':[list(e) for e in edges if closure & (1 << index[e])]}
    assert [audit[k]['candidate_count'] for k in audit] == [6,2,4,2]
    assert audit['S']['closure_edges'] == [[0,1],[1,2],[2,3],[3,4]]
    assert audit['S_plus_a']['closure_edges'] == [[0,1],[1,2],[2,3],[3,4],[4,5],[6,7]]
    assert audit['S_plus_b']['closure_edges'] == [[0,1],[1,2],[2,3],[3,4],[6,7]]
    result['exchange_counterexample'] = audit
    assert result['graph_counts_C8_2C4'] == [2520, 315]
    assert result['minimum_type_identifying_C8_2C4'] == [4, 4]
    out = Path(__file__).with_name('independent_graph_result.json')
    out.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result))


if __name__ == '__main__':
    run()
