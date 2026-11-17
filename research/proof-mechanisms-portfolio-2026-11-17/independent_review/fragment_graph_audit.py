#!/usr/bin/env python3
"""Audit frozen graph edges and selected expansions; no selection/search run."""
import hashlib
import json
from pathlib import Path
import types

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]


def jsha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def main():
    old_path=ROOT/'proof_reconstruction_round2_20261117/independent_review.py'
    own=types.ModuleType('_independent_frozen_graph_actions')
    own.__file__=str(old_path)
    exec(compile(old_path.read_bytes(),str(old_path),'exec'),own.__dict__)
    source=HERE.parent/'fragment_selection'
    cases=json.loads((source/'development-results.json').read_text())+json.loads((source/'test-results.json').read_text())
    results=[]
    counts={'nonofficial_original_apply':0,'nonofficial_edge_apply':0,'edges':0,'official_apply':0}
    for case in cases:
        graph=json.loads((source/case['graph']['file']).read_text())
        claimed=graph['graph_sha256']
        assert jsha({k:v for k,v in graph.items() if k!='graph_sha256'})==claimed
        assert claimed==case['graph']['sha256']==case['greedy']['graph_sha256']==case['dp']['graph_sha256']
        states=[tuple(map(tuple,s)) for s in graph['states']]
        state=tuple(map(tuple,case['challenge']['initial_relators']))
        assert state==states[0]
        for index,move in enumerate(case['original_moves'],1):
            state=own.own_apply(state,move)
            counts['nonofficial_original_apply']+=1
            assert state==states[index]
        for edge in graph['edges']:
            i,j=edge['i'],edge['j']
            assert 0<=i<j<len(states)
            state=states[i]
            lengths=[sum(map(len,state))]
            for move in edge['route']:
                state=own.own_apply(state,move)
                counts['nonofficial_edge_apply']+=1
                assert state is not None
                lengths.append(sum(map(len,state)))
            assert state==states[j],(case['id'],edge['id'])
            assert edge['length']==len(edge['route'])
            assert edge['work']==sum(lengths[1:])
            assert edge['peak']==max(lengths)
            counts['edges']+=1
        for name in ('greedy','dp'):
            arm=case[name]
            selected=[graph['edges'][eid] for eid in arm['edge_path']]
            cursor=0
            for edge in selected:
                assert edge['i']==cursor
                cursor=edge['j']
            assert cursor==graph['n']
            assert [m for edge in selected for m in edge['route']]==arm['moves']
            cost=[sum(edge['length'] for edge in selected),
                  graph['initial_length']+sum(edge['work'] for edge in selected),
                  max([graph['initial_length']]+[edge['peak'] for edge in selected])]
            assert cost==arm['metrics']
        assert not case['graph']['stats']['truncations']
        assert not case['dp']['stats']['truncations']
        assert case['dp']['optimal_in_generated_graph']
        assert case['greedy']['metrics']==case['dp']['metrics']
        assert case['greedy']['moves']==case['dp']['moves']
        results.append({'id':case['id'],'graph_sha256':claimed,'edges':len(graph['edges']),
                        'every_edge_exact_endpoint_and_cost':True,
                        'selected_expansion_and_cost_match':True,'greedy_dp_moves_equal':True,
                        'dp_peak_labels_at_vertex':case['dp']['stats']['peak_labels_at_vertex']})
    result={'status':'passed','scope':'Independent audit of already frozen graph edges and selected chains; no greedy/DP optimizer rerun.',
            'code_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'cases':len(cases),'counts':counts,'results':results}
    (HERE/'fragment-graph-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'cases':len(cases),'counts':counts}))


if __name__=='__main__':main()
