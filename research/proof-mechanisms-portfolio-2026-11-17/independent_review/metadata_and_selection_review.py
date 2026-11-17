#!/usr/bin/env python3
"""Read-only frozen metadata, ledger, and selected-route provenance audit."""
import datetime
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
BASE=HERE.parent
ROOT=HERE.parents[1]


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def jsha(value):return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()
def when(value):return datetime.datetime.fromisoformat(value)
def key(ident,moves):return ident,tuple(moves)


def main():
    checks=[]
    p=BASE/'goal_suffix';f=read(p/'FREEZE.json');access=read(p/'TEST-ACCESS.json')
    assert sha(p/'run_suffix.py')==f['script_sha256']==access['script_sha256']
    assert jsha(f['config'])==f['config_sha256']==access['config_sha256']
    assert f['selected_ids_sha256']==access['selected_ids_sha256']
    assert when(f['frozen_at'])<when(access['first_action_list_access_after'])
    assert sha(p/'development-results.json')==f['development_results_sha256']
    ledger=read(p/'attempt-ledger.json');report=read(p/'results.json')
    assert ledger['counts']==report['accounting']
    goal_search=sum(v for k,v in ledger['counts'].items() if k.endswith('search_apply'))
    goal_verify=sum(v for k,v in ledger['counts'].items() if k.endswith('verification_apply'))
    assert (goal_search,goal_verify)==(report['total_search_apply'],report['total_verification_apply'])==(57442,1522)
    checks.append({'team':'goal_suffix','status':'accept','frozen_code_and_config_match':True,
                   'freeze_precedes_declared_test_access':True,'search':goal_search,'verification':goal_verify})
    p=BASE/'fragment_selection';f=read(p/'FREEZE.json');access=read(p/'TEST-ACCESS.json')
    assert all(sha(p/name)==value for name,value in f['locks'].items())
    assert access['locks']==f['locks']
    assert when(f['frozen_at'])<when(access['first_action_access_not_before'])
    assert sha(p/'development-results.json')==f['development_results_sha256']
    rows=read(p/'development-results.json')+read(p/'test-results.json')
    assert all(row['locks']==f['locks'] and row['status']=='completed' for row in rows)
    ledger=read(p/'attempt-ledger.json');report=read(p/'results.json')
    assert ledger['counters']==report['counters']
    fragment_search=sum(v for k,v in ledger['counters'].items() if k.endswith('search_apply'))
    fragment_verify=sum(v for k,v in ledger['counters'].items() if k.endswith('verification_apply'))
    assert (fragment_search,fragment_verify)==(342096,1265)
    assert len(ledger['attempts'])==6 and all(a['status']=='completed' for a in ledger['attempts'])
    assert sum(r['dp']['metrics'][0] for r in rows)==400
    assert all(r['greedy']['moves']==r['dp']['moves'] for r in rows)
    checks.append({'team':'fragment_selection','status':'accept','frozen_code_and_rules_match':True,
                   'freeze_precedes_declared_test_access':True,'search':fragment_search,'verification':fragment_verify})
    p=BASE/'conjugation_frames';f1=read(p/'FREEZE.json');f2=read(p/'FREEZE-v2.json')
    assert sha(p/'check_frames.py')==f1['script_sha256']==f2['core_script_sha256']
    assert sha(p/'frame_rules.py')==f1['rule_sha256']==f2['v1_rule_sha256']
    assert sha(p/'check_pending_frames.py')==f2['script_sha256']
    assert sha(p/'pending_frame_rules.py')==f2['rule_sha256']
    assert jsha(f1['config'])==f1['config_sha256'] and jsha(f2['config'])==f2['config_sha256']
    ledger=read(p/'attempt-ledger.json')
    assert (ledger['counters']['search_official_apply'],ledger['counters']['verification_official_apply'])==(697,2893)
    assert len(ledger['attempts'])==4 and all(a['status']=='completed' for a in ledger['attempts'])
    checks.append({'team':'conjugation_frames','status':'accept','v1_v2_frozen_code_match':True,
                   'no_new8_access_claimed':True,'search':697,'verification':2893})
    p=BASE/'symbolic_rules';ledger=read(p/'ATTEMPT-LEDGER.json');report=read(p/'OFFICIAL-VERIFICATION.json')
    assert sha(p/'RULES.json')=='701b9b233a7ba0a1e926d0333ae8fef652e6c9bd83ab4a6ef12070bbd617e2bc'
    assert sha(p/'verify_rules.py')==report['summary']['script_sha256']
    for field,total in ledger['totals'].items():assert sum(a[field] for a in ledger['attempts'])==total
    assert ledger['totals']['official_verification_apply']==report['summary']['official_verification_apply_calls_total']==1865
    assert ledger['totals']['symbolic_primitive_apply']==162958
    checks.append({'team':'symbolic_rules','status':'accept','frozen_rule_hash_match':True,
                   'no_new8_access_claimed':True,'search':0,'verification':1865,'symbolic':162958})
    # Root chose among already checked full routes after experimental execution.
    audited={}
    input_names=('goal-suffix-input.json','goal-suffix-other-improvements-input.json','symbolic-input.json','fragment-input.json','frames-input.json')
    for name in input_names:
        for case in read(HERE/name)['cases']:
            for route in case['routes']:
                audited.setdefault(key(case['challenge']['challenge_id'],route['moves']),[]).append('current_review:'+name)
    old_input=read(ROOT/'proof_reconstruction_round2_20261117/review-input.json')
    old_result=read(ROOT/'proof_reconstruction_round2_20261117/INDEPENDENT-REVIEW.json')
    old_index={(r['challenge_id'],r['label']):r for r in old_result['results']}
    for case in old_input['cases']:
        for label,route in case['routes'].items():
            r=old_index[case['challenge_id'],label]
            assert all(route[k]==r[k] for k in ('length','work','peak_total_relator_length'))
            audited.setdefault(key(case['challenge_id'],route['moves']),[]).append('previous_round2_independent_review')
    selected=read(BASE/'SELECTED-CERTIFICATES.json');coverage=[]
    for case in selected['cases']:
        origins=audited.get(key(case['challenge_id'],case['moves']))
        assert origins,(case['challenge_id'],'not previously independently replayed')
        coverage.append({'challenge_id':case['challenge_id'],'length':len(case['moves']),
                         'independent_coverage':sorted(set(origins))})
    assert len(coverage)==29 and sum(r['length'] for r in coverage)==387
    result={'status':'passed','code_sha256':sha(Path(__file__)),
            'scope':'Metadata consistency and route-identity provenance only; declared access timing is not externally observed blind-test attestation.',
            'official_apply':0,'search':0,'teams':checks,
            'selection':{'cases':29,'total_length':387,'all_selected_routes_previously_independently_replayed':True,
                         'additional_replay_runs':0,'coverage':coverage},
            'all_team_search_excluding_root':400235,
            'all_team_verification_excluding_root_and_review':7545}
    (HERE/'metadata-and-selection-review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'status':result['status'],'selected_cases':len(coverage),'selected_length':387,'official_apply':0}))


if __name__=='__main__':main()
