#!/usr/bin/env python3
"""Replay selected final certificates with a reused independent Stable AC interpreter.

No optimizer code is imported. The second interpreter below is adapted from our
published round2_stable_audit/independent_stable_verifier.py; it is not a new
independent search. Only pinned official canon/core/stable_core are executed.
Input review-input.json is a small adapter to the optimizer's reported routes.
"""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import types

PIN = 'a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e'
BLOBS = {'canon': '93175152acd876566ff60bbfaf7cd90cd8cd2fa9',
         'core': '0a5da5fe6e3e42c96877734dad46b155a69c02b2',
         'stable_core': 'af48e32f766dbcd0cad0becd8c1c4edb4358efac'}
TRAIN_BLOB = '22428166cb348d41bbc92e24ab9e2a49e1ebd235'
LIMITS = {'max_path_length': 100000, 'max_total_relator_length': 10000,
          'max_work': 5000000}

def sha(data): return hashlib.sha256(data).hexdigest()
def blob(data):
    return hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()

def actions():
    out = [('I',0,0,0), ('I',1,0,0), ('M',0,1,1), ('M',0,1,-1),
           ('M',1,0,1), ('M',1,0,-1)]
    out += [('C',i,g,0) for i in range(2) for g in (1,-1,2,-2)]
    out += [('S',0,0,0)] + [('D',i,0,0) for i in range(8)]
    out += [('I',i,0,0) for i in range(2,8)]
    out += [('M',i,j,s) for i in range(8) for j in range(8)
            if i != j and not (i < 2 and j < 2) for s in (1,-1)]
    out += [('C',i,s*g,0) for i in range(8) for g in range(1,9)
            if not (i < 2 and g < 3) for s in (1,-1)]
    assert len(out) == len(set(out)) == 257
    return out

ACTIONS = actions()
def inv(w): return tuple(-a for a in w[::-1])
def reduce_word(w):
    w = list(w)
    i = 0
    while i+1 < len(w):
        if w[i] == -w[i+1]:
            del w[i:i+2]
            i = max(0, i-1)
        else: i += 1
    return tuple(w)

def own_apply(state, mid):
    op,i,j,s = ACTIONS[mid]
    k = len(state)
    if op == 'S': return state+((k+1,),) if k < 8 else None
    if i >= k: return None
    if op == 'D':
        if len(state[i]) != 1 or state[i][0] <= 0: return None
        g = state[i][0]
        rest = state[:i]+state[i+1:]
        if any(abs(a) == g for w in rest for a in w): return None
        labels = {a:b for b,a in enumerate([a for a in range(1,k+1) if a != g],1)}
        return tuple(tuple(labels[a] if a > 0 else -labels[-a] for a in w) for w in rest)
    out = list(state)
    if op == 'I': out[i] = inv(state[i])
    elif op == 'M':
        if j >= k: return None
        out[i] = reduce_word(state[i]+(state[j] if s == 1 else inv(state[j])))
    elif op == 'C':
        if abs(j) > k: return None
        out[i] = reduce_word((j,)+state[i]+(-j,))
    return tuple(out)

def load_official(root):
    directory = root/'competition/tools/verifier'
    package = types.ModuleType('_independent_reconstruction_review')
    package.__path__ = [str(directory)]
    sys.modules[package.__name__] = package
    loaded = {}
    for name, expected in BLOBS.items():
        path = directory/(name+'.py')
        data = path.read_bytes()
        assert blob(data) == expected, path
        module = types.ModuleType(package.__name__+'.'+name)
        module.__file__ = str(path)
        module.__package__ = package.__name__
        sys.modules[module.__name__] = module
        setattr(package, name, module)
        exec(compile(data, str(path), 'exec'), module.__dict__)
        loaded[name] = module
    stable = loaded['stable_core']
    for row, (op,i,j,s) in zip(stable.MOVE_TABLE, ACTIONS):
        assert row['category'] == {'I':'inversion','M':'multiplication',
            'C':'conjugation','S':'stabilize','D':'destabilize'}[op]
        if op != 'S': assert row['relator'] == i
        if op == 'M': assert row['other'] == j and row['invert_other'] == (s == -1)
        if op == 'C': assert row['conjugator'] == j
    return stable

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--official-root', type=Path, required=True)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    stable = load_official(args.official_root)
    data = (args.official_root/'competition/examples/stable_training_424.json').read_bytes()
    assert blob(data) == TRAIN_BLOB
    training = {r['training_id']:r for r in json.loads(data)['instances']}
    manifest = json.loads((args.official_root/'competition/tools/verifier/data/manifest.json').read_text())
    challenges = {r['challenge_id']:r for r in manifest['challenges']}
    inputs = json.loads(args.input.read_text())
    counts = {'own_apply': 0, 'official_apply': 0, 'official_verify': 0}
    original_apply = stable.apply_move
    def counted_apply(state, mid):
        counts['official_apply'] += 1
        assert counts['official_apply'] <= 3000, 'review budget'
        return original_apply(state, mid)
    stable.apply_move = counted_apply
    rows = []
    for case in inputs['cases']:
        if case.get('training_id'):
            source = training[case['training_id']]
            challenge = {'challenge_id':'sac-train-'+case['training_id'].split('-')[-1],
                'initial_relators':source['initial_relators'], 'target_relators':[],
                'move_spec_version':stable.MOVE_SPEC_VERSION}
            assert case['challenge_id'] == challenge['challenge_id']
            assert case['routes']['original']['moves'] == source['moves']
        else:
            challenge = challenges[case['challenge_id']]
        for label, route in case['routes'].items():
            moves = route['moves']
            assert len(moves) <= LIMITS['max_path_length']
            state = tuple(map(tuple, challenge['initial_relators']))
            lengths = [sum(map(len, state))]
            for mid in moves:
                assert type(mid) is int and 0 <= mid < 257
                got = own_apply(state, mid)
                counts['own_apply'] += 1
                expected, reason = stable.apply_move(state, mid)
                assert got == expected and got is not None and reason is None
                assert len(got) <= 8 and all(reduce_word(w) == w for w in got)
                state = got
                lengths.append(sum(map(len, state)))
                assert lengths[-1] <= LIMITS['max_total_relator_length']
            assert state == (), (case['challenge_id'], label)
            metrics = {'length':len(moves), 'work':sum(lengths),
                       'peak_total_relator_length':max(lengths)}
            assert metrics['work'] <= LIMITS['max_work']
            for key, value in metrics.items(): assert route[key] == value, (label,key)
            counts['official_verify'] += 1
            verdict = stable.verify(challenge, moves, stable.MOVE_SPEC_VERSION, LIMITS)
            assert verdict['ok'] and all(verdict[k] == v for k,v in metrics.items())
            rows.append({'challenge_id':case['challenge_id'], 'label':label,
                         **metrics, 'certificate_hash':verdict['certificate_hash'],
                         'all_intermediate_states_match':True})
    report = {'status':'passed', 'scope':'Independent final-certificate replay and metric check; no independent optimizer/search replication.',
        'official_commit':PIN, 'code_sha256':sha(Path(__file__).read_bytes()),
        'input_sha256':sha(args.input.read_bytes()), 'cases':len(inputs['cases']),
        'routes':len(rows), 'counts':counts, 'results':rows,
        'interpreter_provenance':'Adapted from previously published round2_stable_audit/independent_stable_verifier.py; no optimizer imports.'}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n')
    print(json.dumps({k:report[k] for k in ('status','cases','routes','counts')}, ensure_ascii=False))

if __name__ == '__main__': main()
