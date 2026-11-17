#!/usr/bin/env python3
"""Independent final-route acceptance only; no optimizer import or new search.

The action interpreter is compiled from the previous round's published
independent_review.py. It and the fixed official implementation execute each
step from their own complete ordered state. A second complete official verify
then checks the original challenge. All official apply calls, including failed
runs and verifier-internal calls, are charged to a persistent 15000-call ledger.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import types

CAP = 15000
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OLD = ROOT / 'proof_reconstruction_round2_20261117/independent_review.py'
LIMITS = {'max_path_length': 100000, 'max_total_relator_length': 10000,
          'max_work': 5000000}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def load_old():
    data = OLD.read_bytes()
    module = types.ModuleType('_old_portfolio_independent_interpreter')
    module.__file__ = str(OLD)
    exec(compile(data, str(OLD), 'exec'), module.__dict__)
    return module, digest(data)


def metrics(states):
    lengths = [sum(map(len, s)) for s in states]
    return {'length': len(states)-1, 'work': sum(lengths),
            'peak_total_relator_length': max(lengths),
            'final_rank': len(states[-1])}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--official-root', type=Path, default=ROOT/'ac_official')
    parser.add_argument('--ledger', type=Path, default=HERE/'verification-ledger.json')
    args = parser.parse_args()
    old, old_hash = load_old()
    official = old.load_official(args.official_root)
    raw = args.input.read_bytes()
    inputs = json.loads(raw)
    assert inputs['scope'] == 'approved_final_certificates_only'
    ledger = (json.loads(args.ledger.read_text()) if args.ledger.exists() else
              {'official_apply_cap': CAP, 'official_apply': 0,
               'own_apply': 0, 'official_verify': 0, 'runs': []})
    assert ledger['official_apply_cap'] == CAP
    planned = 2 * sum(len(r['moves']) for c in inputs['cases'] for r in c['routes'])
    assert ledger['official_apply'] + planned <= CAP, 'preflight review budget'
    run = {'started_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
           'input': str(args.input), 'input_sha256': digest(raw),
           'code_sha256': digest(Path(__file__).read_bytes()),
           'interpreter_sha256': old_hash, 'planned_official_apply': planned,
           'counts': {'official_apply': 0, 'own_apply': 0, 'official_verify': 0},
           'status': 'running', 'completed_routes': []}
    ledger['runs'].append(run)
    original_apply = official.apply_move

    def counted_apply(state, move):
        assert ledger['official_apply'] < CAP, 'review budget exhausted'
        ledger['official_apply'] += 1
        run['counts']['official_apply'] += 1
        return original_apply(state, move)

    official.apply_move = counted_apply
    results, traces = [], []
    try:
        for case in inputs['cases']:
            challenge = case['challenge']
            assert challenge['move_spec_version'] == official.MOVE_SPEC_VERSION
            initial = tuple(map(tuple, challenge['initial_relators']))
            target = tuple(map(tuple, challenge['target_relators']))
            for route in case['routes']:
                moves = route['moves']
                assert isinstance(moves, list) and len(moves) <= LIMITS['max_path_length']
                own_state, official_state = initial, initial
                states = [initial]
                trace = [{'step': 0, 'state': initial, 'rank': len(initial),
                          'total_relator_length': sum(map(len, initial)),
                          'work': sum(map(len, initial)),
                          'peak_total_relator_length': sum(map(len, initial))}]
                for index, move in enumerate(moves, 1):
                    assert type(move) is int and 0 <= move < 257
                    own_state = old.own_apply(own_state, move)
                    ledger['own_apply'] += 1
                    run['counts']['own_apply'] += 1
                    official_state, reason = official.apply_move(official_state, move)
                    assert own_state is not None and reason is None
                    assert own_state == official_state, (case['case_id'], route['label'], index)
                    assert 0 <= len(own_state) <= 8
                    assert all(old.reduce_word(w) == w for w in own_state)
                    assert all(0 < abs(a) <= len(own_state) for w in own_state for a in w)
                    total = sum(map(len, own_state))
                    assert total <= LIMITS['max_total_relator_length']
                    work = trace[-1]['work'] + total
                    assert work <= LIMITS['max_work']
                    states.append(own_state)
                    trace.append({'step': index, 'move': move, 'state': own_state,
                                  'rank': len(own_state), 'total_relator_length': total,
                                  'work': work,
                                  'peak_total_relator_length': max(trace[-1]['peak_total_relator_length'], total)})
                assert own_state == target, (case['case_id'], route['label'], 'target')
                actual = metrics(states)
                for key, expected in route.get('expected_metrics', {}).items():
                    assert actual[key] == expected, (case['case_id'], route['label'], key, actual[key], expected)
                ledger['official_verify'] += 1
                run['counts']['official_verify'] += 1
                verdict = official.verify(challenge, moves, official.MOVE_SPEC_VERSION, LIMITS)
                assert verdict['ok'], verdict
                assert all(verdict[k] == actual[k] for k in ('length', 'work', 'peak_total_relator_length'))
                row = {'case_id': case['case_id'], 'label': route['label'],
                       'challenge_id': challenge['challenge_id'], **actual,
                       'certificate_hash': verdict['certificate_hash'],
                       'ordered_state_rank_work_peak_match_every_step': True,
                       'official_verdict': verdict}
                results.append(row)
                traces.append({'case_id': case['case_id'], 'label': route['label'],
                               'steps': trace})
                run['completed_routes'].append({'case_id': case['case_id'], 'label': route['label']})
        run['status'] = 'passed'
    except BaseException as error:
        run['status'] = 'failed'
        run['error'] = repr(error)
        raise
    finally:
        run['ended_at'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        write(args.ledger, ledger)
        report = {'status': run['status'],
                  'scope': 'Independent final-route replay; no optimizer/search reproduction.',
                  'official_commit': old.PIN, 'input_sha256': digest(raw),
                  'code_sha256': run['code_sha256'], 'old_interpreter_sha256': old_hash,
                  'counts': run['counts'], 'results': results,
                  'total_ledger_official_apply': ledger['official_apply']}
        write(args.output, report)
        write(args.output.with_suffix('.traces.json'), {'traces': traces})
    print(json.dumps({'status': run['status'], 'routes': len(results),
                      'counts': run['counts'], 'total_official_apply': ledger['official_apply']}))


if __name__ == '__main__':
    main()
