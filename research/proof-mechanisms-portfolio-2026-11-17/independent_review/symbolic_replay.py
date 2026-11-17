#!/usr/bin/env python3
"""Replay already-frozen identities, not rule discovery or optimization."""
import hashlib
import json
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    old_path = ROOT/'proof_reconstruction_round2_20261117/independent_review.py'
    own = types.ModuleType('_independent_symbolic_old')
    own.__file__ = str(old_path)
    exec(compile(old_path.read_bytes(), str(old_path), 'exec'), own.__dict__)
    rule_path = HERE.parent/'symbolic_rules/RULES.json'
    data = json.loads(rule_path.read_text())
    start = ((3,), (4,))  # Formal U,V; ambient X,Y are letters 1,2.
    rows, count = [], 0
    for rule in data['rules']:
        route_states = {}
        for label in ('old', 'new'):
            state, states = start, [start]
            for move in rule[label+'_moves']:
                assert move < 14, 'fixed-rank I/M/C only'
                state = own.own_apply(state, move)
                count += 1
                assert state is not None
                states.append(state)
            claimed = tuple(tuple(map(tuple, s)) for s in rule['proof_'+label+'_symbolic_states'])
            assert tuple(states) == claimed
            route_states[label] = state
        assert route_states['old'] == route_states['new'] == tuple(map(tuple, rule['proof_symbolic_output']))
        rows.append({'id':rule['id'], 'old':rule['old_moves'], 'new':rule['new_moves'],
                     'ordered_symbolic_output':route_states['old'], 'all_claimed_symbolic_states_match':True})
    # A separately derived peak counterexample for sym-dev-007.
    peak_examples = []
    for n in (1,4999):
        start = ((1,), (-1,)+(2,)*n+(-1,))
        lengths = {}
        for label, route in (('old',(4,2,5,2)),('new',(2,5))):
            state, values = start, [sum(map(len,start))]
            for move in route:
                state = own.own_apply(state, move)
                count += 1
                values.append(sum(map(len,state)))
            lengths[label] = values
        assert max(lengths['new']) > max(lengths['old'])
        peak_examples.append({'n':n, 'U':'x', 'V':'x^-1 y^n x^-1', 'lengths':lengths})
    result = {'status':'passed', 'rule_count':len(rows), 'nonofficial_symbolic_apply':count,
              'official_apply':0, 'optimizer_imported':False,
              'rules_sha256':hashlib.sha256(rule_path.read_bytes()).hexdigest(),
              'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'independent_interpreter_sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),
              'universal_argument':'Equality in F(X,Y,U,V), followed by arbitrary substitution U,V into F(X,Y) fixing X,Y; fixed-rank I/M/C commute with substitution.',
              'core007_work_difference':'(a+d-b)+(a+e-c)+(d+e)>=0 by triangle inequalities',
              'core007_peak_counterexamples':peak_examples, 'results':rows}
    (HERE/'symbolic-rule-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('status','rule_count','nonofficial_symbolic_apply','official_apply')}))


if __name__ == '__main__':
    main()
