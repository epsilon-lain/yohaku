#!/usr/bin/env python3
"""Synthetic checks for the proved rule and frozen-candidate graph theorem.

No training/test certificates are read. Only checks.json beside this file is
written. Official apply calls, including calls inside verify, are counted.
"""
import argparse
from collections import deque
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import types

sys.dont_write_bytecode = True
PINNED_COMMIT = 'a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e'
EXPECTED_BLOBS = {
    'canon': '93175152acd876566ff60bbfaf7cd90cd8cd2fa9',
    'core': '0a5da5fe6e3e42c96877734dad46b155a69c02b2',
    'stable_core': 'af48e32f766dbcd0cad0becd8c1c4edb4358efac',
}
LIMITS = {'max_path_length': 100000,
          'max_total_relator_length': 10000, 'max_work': 5000000}
COUNTS = {'official_apply_calls': 0, 'manual_replay_apply_calls': 0,
          'inside_official_verify_apply_calls': 0, 'official_verify_calls': 0}
IN_VERIFY = False


def digest_json(value):
    return hashlib.sha256(json.dumps(value, separators=(',', ':'),
                                    sort_keys=True).encode()).hexdigest()


def git_blob(data):
    return hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()


def reduce_word(word):
    """Expected-value oracle independent of the loaded official functions."""
    out = []
    for a in word:
        if out and out[-1] == -a:
            out.pop()
        else:
            out.append(a)
    return tuple(out)


def inverse(word):
    return tuple(-a for a in reversed(word))


def total(state):
    return sum(map(len, state))


def load_official(root):
    directory = root / 'competition/tools/verifier'
    for name, expected in EXPECTED_BLOBS.items():
        actual = git_blob((directory / (name + '.py')).read_bytes())
        if actual != expected:
            raise RuntimeError(f'pinned {name} blob mismatch: {actual}')
    package_name = '_proof_reconstruction_r2_theory'
    package = types.ModuleType(package_name)
    package.__path__ = [str(directory)]
    sys.modules[package_name] = package
    for name in EXPECTED_BLOBS:
        spec = importlib.util.spec_from_file_location(
            f'{package_name}.{name}', directory / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        setattr(package, name, module)
        spec.loader.exec_module(module)
    stable = package.stable_core
    original = stable.apply_move

    def counted_apply(state, move):
        COUNTS['official_apply_calls'] += 1
        key = ('inside_official_verify_apply_calls' if IN_VERIFY else
               'manual_replay_apply_calls')
        COUNTS[key] += 1
        if COUNTS['official_apply_calls'] > 2000:
            raise RuntimeError('theory synthetic official-apply allocation exceeded')
        return original(state, move)

    stable.apply_move = counted_apply
    return stable


def move_tables(stable):
    inv, mul, conj, destab = {}, {}, {}, {}
    for row in stable.MOVE_TABLE:
        cat = row['category']
        if cat == 'inversion':
            inv[row['relator']] = row['id']
        elif cat == 'multiplication':
            mul[row['relator'], row['other'], row['invert_other']] = row['id']
        elif cat == 'conjugation':
            conj[row['relator'], row['conjugator']] = row['id']
        elif cat == 'destabilize':
            destab[row['relator']] = row['id']
    return inv, mul, conj, destab


def compile_conjugation(tables, i, j, sign, h):
    inv, mul, conj, _ = tables
    right = mul[i, j, sign == 1]
    return ([conj[i, -a] for a in h] +
            [inv[i], right, inv[i], right] +
            [conj[i, a] for a in reversed(h)])


def replay(stable, initial, moves):
    states = [initial]
    for move in moves:
        state, error = stable.apply_move(states[-1], move)
        assert error is None, (move, error)
        states.append(state)
    return states


def verify(stable, initial, target, moves, name):
    global IN_VERIFY
    challenge = {'challenge_id': name, 'move_spec_version': stable.MOVE_SPEC_VERSION,
                 'initial_relators': [list(w) for w in initial],
                 'target_relators': [list(w) for w in target]}
    COUNTS['official_verify_calls'] += 1
    IN_VERIFY = True
    try:
        return stable.verify(challenge, moves, stable.MOVE_SPEC_VERSION, LIMITS)
    finally:
        IN_VERIFY = False


def metrics(states, moves):
    lengths = list(map(total, states))
    return {'length': len(moves), 'work': sum(lengths),
            'peak_total_relator_length': max(lengths),
            'state_total_lengths_including_initial': lengths,
            'moves': moves, 'moves_sha256': digest_json(moves)}


def check_valid_route(stable, initial, moves, name):
    states = replay(stable, initial, moves)
    result = metrics(states, moves)
    receipt = verify(stable, initial, states[-1], moves, name)
    assert receipt['ok'], receipt
    for key in ('length', 'work', 'peak_total_relator_length'):
        assert receipt[key] == result[key]
    result['official_verdict'] = receipt
    return states, result


def sample_h(rank, seed, length):
    alphabet = tuple(a for g in range(1, rank + 1) for a in (g, -g))
    out = []
    for step in range(length):
        choices = [a for a in alphabet if not out or a != -out[-1]]
        out.append(choices[(seed + 3 * step) % len(choices)])
    return tuple(out)


def rule_matrix(stable, tables):
    rows = []
    for rank in range(2, 9):
        initial = tuple((i + 1, (i + 1) % rank + 1, i + 1)
                        for i in range(rank))
        if rank == 3:
            initial = ((),) + initial[1:]  # exercise empty target and donor
        for direction, (i, j) in enumerate(((0, rank - 1), (rank - 1, 0))):
            for sign in (1, -1):
                for h_length in range(4):
                    h = sample_h(rank, rank + direction, h_length)
                    assert reduce_word(h) == h
                    moves = compile_conjugation(tables, i, j, sign, h)
                    assert len(moves) == 2 * len(h) + 4
                    donor = initial[j] if sign == 1 else inverse(initial[j])
                    w = reduce_word(h + donor + inverse(h))
                    expected = list(initial)
                    expected[i] = reduce_word(w + initial[i] + inverse(w))
                    states, result = check_valid_route(
                        stable, initial, moves,
                        f'synthetic-theory-k{rank}-i{i}-j{j}-s{sign}-h{h_length}')
                    assert states[-1] == tuple(expected)
                    assert all(len(state) == rank for state in states)
                    assert all(all(state[q] == initial[q] for q in range(rank)
                                   if q != i) for state in states)
                    rows.append({'rank': rank, 'target': i, 'donor': j,
                                 'sign': sign, 'h': h, 'w': w,
                                 'initial': initial, 'endpoint': states[-1], **result})
    assert len(rows) == 112
    return rows


def embedded_complete_certificate(stable, tables):
    inv, mul, conj, destab = tables
    initial = ((1,), (2,) + (1,) * 7)
    h, sign = (1, 2), 1
    w = reduce_word(h + initial[1] + inverse(h))
    literal = [conj[0, a] for a in reversed(w)]
    compiled = compile_conjugation(tables, 0, 1, sign, h)
    assert (len(literal), len(compiled)) == (12, 8)
    prefix = [inv[1], inv[1]]
    undo = [stable.INVERSE_MOVE[move] for move in reversed(literal)]
    suffix = undo + [mul[1, 0, True]] * 7 + [destab[0], destab[0]]
    original, replacement = prefix + literal + suffix, prefix + compiled + suffix
    old_states, old = check_valid_route(stable, initial, original, 'synthetic-full-old')
    new_states, new = check_valid_route(stable, initial, replacement, 'synthetic-full-new')
    assert old_states[-1] == new_states[-1] == ()
    a, b, m = len(prefix), len(prefix) + len(literal), len(compiled)
    local = new_states[a:a + m + 1]
    assert local[0] == old_states[a] and local[-1] == old_states[b]
    assert new_states[a + m + 1:] == old_states[b + 1:]
    predicted = {
        'length': old['length'] - (b - a) + m,
        'work': old['work'] - sum(map(total, old_states[a + 1:b + 1])) +
                sum(map(total, local[1:])),
        'peak_total_relator_length': max(
            max(map(total, old_states[:a + 1]), default=0),
            max(map(total, local[1:]), default=0),
            max(map(total, old_states[b + 1:]), default=0)),
    }
    for key, value in predicted.items():
        assert new[key] == value
    return {'synthetic_only': True, 'initial': initial, 'h': h, 'w': w,
            'replace_start': a, 'replace_end_exclusive': b,
            'predicted_full_metrics': predicted, 'original': old, 'rewritten': new,
            'exact_exit_and_unchanged_suffix_checked': True}


def resource_guard(stable, tables):
    _, _, conj, _ = tables
    initial = ((1,) * 9992, (1,) * 5)
    routes = {'literal': [conj[0, 1]] * 5,
              'compiled': compile_conjugation(tables, 0, 1, 1, ())}
    output = {}
    for name, moves in routes.items():
        states = replay(stable, initial, moves)
        assert states[-1] == initial
        output[name] = metrics(states, moves)
        output[name]['official_capped_verdict'] = verify(
            stable, initial, initial, moves, f'synthetic-resource-{name}')
    assert output['literal']['official_capped_verdict']['ok']
    bad = output['compiled']['official_capped_verdict']
    assert bad['code'] == 'E_LENGTH_LIMIT'
    assert bad['move_index'] == 1 and bad['total_relator_length'] == 10002
    return output


def finite_graph_counterexample():
    unit_edges = [(i, i + 1) for i in range(7)] + [(0, 'a'), ('a', 6), (0, 3), (3, 7)]
    graph = {}
    for u, v in unit_edges:
        graph.setdefault(u, set()).add(v)
        graph.setdefault(v, set()).add(u)

    def distance(source, target):
        queue, seen = deque([(source, 0)]), {source}
        while queue:
            u, d = queue.popleft()
            if u == target:
                return d
            for v in graph[u]:
                if v not in seen:
                    seen.add(v)
                    queue.append((v, d + 1))
        raise AssertionError('unreachable')

    candidates = [('A', 0, 6, [0, 'a', 6]), ('B', 0, 3, [0, 3]),
                  ('C', 3, 7, [3, 7])]
    for _, i, j, path in candidates:
        assert len(path) - 1 == distance(i, j)
    path, accepted = list(range(8)), []
    while True:
        choices = []
        for name, i, j, replacement in candidates:
            if i not in path or j not in path:
                continue
            a, b = path.index(i), path.index(j)
            if a >= b or len(replacement) - 1 >= b - a:
                continue
            new = path[:a] + replacement + path[b + 1:]
            choices.append((len(new) - 1, name, new))
        if not choices:
            break
        _, name, path = min(choices, key=lambda row: (row[0], row[1]))
        accepted.append(name)
    assert accepted == ['A'] and len(path) - 1 == 3

    # Pareto labels on the frozen candidate DAG; all synthetic state lengths = 1.
    edges = {i: [(i + 1, [i, i + 1])] for i in range(7)}
    for _, i, j, replacement in candidates:
        edges[i].append((j, replacement))
    labels = [[] for _ in range(8)]
    labels[0] = [((0, 1, 1), [0])]
    for i in range(7):
        for (length, work, peak), old_path in list(labels[i]):
            for j, replacement in edges[i]:
                steps = len(replacement) - 1
                value = (length + steps, work + steps, max(peak, 1))
                if any(all(x <= y for x, y in zip(existing, value))
                       for existing, _ in labels[j]):
                    continue
                labels[j] = [(existing, p) for existing, p in labels[j]
                             if not all(x <= y for x, y in zip(value, existing))]
                labels[j].append((value, old_path + replacement[1:]))
    optimum, optimal_path = min(labels[7], key=lambda row: row[0])
    assert optimum == (2, 3, 1) and optimal_path == [0, 3, 7]
    assert distance(0, 7) == 2

    # A separate finite resource tradeoff: one shorter prefix uses more work.
    # Source/join/target and both long-route interiors have length 1;
    # the short-route interior has length 9. Work here includes source once.
    short_prefix, long_prefix = (2, 11, 9), (3, 4, 1)
    short_full = (3, 12, 9)
    long_full = (4, 5, 1)
    assert short_prefix < long_prefix and short_full[1] > 11 >= long_full[1]
    assert not all(x <= y for x, y in zip(short_prefix, long_prefix))
    assert not all(x <= y for x, y in zip(long_prefix, short_prefix))
    return {'abstract_proof_graph_not_official_ac': True, 'unit_edges': unit_edges,
            'reverse_edges_also_present': True, 'original_path': list(range(8)),
            'candidate_routes': candidates, 'all_candidates_endpoint_shortest': True,
            'greedy_accepted': accepted, 'greedy_path': path, 'greedy_length': 3,
            'pareto_optimal_path': optimal_path, 'pareto_metrics': optimum,
            'independent_graph_bfs_optimum_length': distance(0, 7),
            'resource_tradeoff': {'short_prefix': short_prefix, 'long_prefix': long_prefix,
                                 'work_cap': 11, 'short_full': short_full,
                                 'long_full': long_full}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--official-root', type=Path,
                        default=Path(__file__).resolve().parents[2] / 'ac_official')
    args = parser.parse_args()
    stable = load_official(args.official_root)
    tables = move_tables(stable)
    result = {'scope': 'synthetic semantics and finite proof graph; no data certificates read',
              'official_commit': PINNED_COMMIT, 'official_git_blobs': EXPECTED_BLOBS,
              'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'limits': LIMITS, 'rule_matrix': rule_matrix(stable, tables),
              'embedded_complete_certificate': embedded_complete_certificate(stable, tables),
              'resource_guard': resource_guard(stable, tables),
              'finite_graph': finite_graph_counterexample()}
    result['counts'] = dict(COUNTS)
    assert COUNTS['official_apply_calls'] == 1716, COUNTS
    assert COUNTS['official_verify_calls'] == 116, COUNTS
    target = Path(__file__).with_name('checks.json')
    target.write_text(json.dumps(result, ensure_ascii=False, separators=(',', ':')) + '\n')
    print(json.dumps({'output': str(target), 'counts': COUNTS,
                      'synthetic_full_original': result['embedded_complete_certificate']['original']['length'],
                      'synthetic_full_rewritten': result['embedded_complete_certificate']['rewritten']['length'],
                      'sha256': hashlib.sha256(target.read_bytes()).hexdigest()},
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
