#!/usr/bin/env python3
"""Compare three full primitive paths on an exact synthetic deletion task.

The independent interpreter is reused from the previous published audit;
no optimizer, search, native host session or contest manifest is executed.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import types

HERE = Path(__file__).resolve().parent
LIMITS = {'max_path_length':100000, 'max_total_relator_length':10000,
          'max_work':5000000}

def digest(data): return hashlib.sha256(data).hexdigest()
def canonical(obj): return json.dumps(obj,separators=(',',':'),ensure_ascii=True).encode()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--official-root', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads((HERE/'PROTOCOL.json').read_text())
    own_source = HERE/'independent_primitives.py'
    own = types.ModuleType('_ci_m_reused_independent_interpreter')
    own.__file__ = str(own_source)
    exec(compile(own_source.read_bytes(),str(own_source),'exec'),own.__dict__)
    # Checks all three fixed official Git blobs before executing their bytes.
    official = own.load_official(args.official_root.resolve())
    counts = Counter()
    phase = 'direct'
    original_apply = official.apply_move
    def counted(state, mid):
        counts['official_apply'] += 1
        assert counts['official_apply'] <= protocol['official_verification_apply_cap']
        counts['official_'+phase+'_apply'] += 1
        return original_apply(state,mid)
    official.apply_move = counted
    values = list(range(1,65))+[100,1000]
    rows = []
    for length in values:
        donor = (1,)*length
        initial = (donor, donor+(2,)+(-1,)*length)
        target = (donor,)
        paths = {'CI_optimal':[11]*length+[16],
                 'CIM_reference':[1,4,1,4,16],
                 'CIM_lower_work':[4,1,4,1,16]}
        expected = {'CI_optimal':(length+1,2*length*length+4*length+1,3*length+1),
                    'CIM_reference':(5,12*length+5,3*length+1),
                    'CIM_lower_work':(5,10*length+5,3*length+1)}
        challenge = {'challenge_id':f'synthetic-ci-m-L{length}',
            'move_spec_version':official.MOVE_SPEC_VERSION,
            'initial_relators':[list(w) for w in initial],
            'target_relators':[list(w) for w in target]}
        case = {'L':length,'initial_formula':'(x^L,x^L*y*x^-L)',
                'target_formula':'rank1 (x^L)', 'routes':{}}
        for label,moves in paths.items():
            state = initial
            lengths = [sum(map(len,state))]
            trace = [state] if length == 12 else None
            rolling = hashlib.sha256(canonical(state)+b'\n')
            phase = 'direct'
            for index,mid in enumerate(moves):
                alternative = own.own_apply(state,mid)
                counts['independent_apply'] += 1
                actual,reason = official.apply_move(state,mid)
                assert reason is None and actual is not None and actual == alternative
                state = actual
                assert state[0] == donor, 'donor changed, including after deletion'
                assert len(state) == (1 if index == len(moves)-1 else 2)
                lengths.append(sum(map(len,state)))
                rolling.update(canonical(state)+b'\n')
                if trace is not None: trace.append(state)
            assert state == target
            metrics = (len(moves),sum(lengths),max(lengths))
            assert metrics == expected[label], (length,label,metrics)
            phase = 'inside_verify'
            counts['official_verify_calls'] += 1
            verdict = official.verify(challenge,moves,official.MOVE_SPEC_VERSION,LIMITS)
            assert verdict['ok']
            assert tuple(verdict[k] for k in ('length','work','peak_total_relator_length')) == metrics
            output = {'moves':moves,'length':metrics[0],'work':metrics[1],
                'peak_total_relator_length':metrics[2],
                'total_lengths_including_initial':lengths,
                'all_independent_states_match':True,
                'trace_sha256':rolling.hexdigest(),'official_kernel_verdict':verdict}
            if trace is not None: output['full_states'] = trace
            case['routes'][label] = output
        case['CI_minimum_length'] = length+1
        case['larger_class_strict_length_advantage_certified'] = length > 4
        assert (case['routes']['CIM_lower_work']['length'] < case['CI_minimum_length']) == (length > 4)
        assert case['routes']['CIM_lower_work']['work'] < case['routes']['CIM_reference']['work']
        rows.append(case)
    assert counts['official_apply'] == 7812
    assert counts['independent_apply'] == 3906
    report = {'status':'passed','scope':protocol['scope'],
        'official_commit':protocol['official_commit'],
        'protocol_sha256':digest((HERE/'PROTOCOL.json').read_bytes()),
        'code_sha256':digest(Path(__file__).read_bytes()),
        'reused_independent_interpreter_sha256':digest(own_source.read_bytes()),
        'official_search_apply':0,'counts':dict(counts),
        'cases':len(rows),'routes':3*len(rows),'results':rows,
        'interpretation':'Strict separation of a restricted CI repair optimum and an exhibited CIM upper bound; no claim of larger-class optimality or scored AC improvement.'}
    (HERE/'checks.json').write_text(json.dumps(report,ensure_ascii=False,separators=(',',':'))+'\n')
    primary = next(r for r in rows if r['L'] == 12)
    print(json.dumps({'status':report['status'],'cases':report['cases'],
        'routes':report['routes'],'counts':report['counts'],
        'L12':{k:{m:v[m] for m in ('length','work','peak_total_relator_length')}
               for k,v in primary['routes'].items()}},ensure_ascii=False))

if __name__ == '__main__': main()
