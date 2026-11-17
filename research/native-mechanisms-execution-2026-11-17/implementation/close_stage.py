"""Close only this finished finite grant after actual native receipt checks."""
import datetime,json,time
from pathlib import Path
from continuation import BASE,PHASE,activate,verify_parent,save,sha,snapshot
def main():
    p=activate();before=verify_parent();current,events,entries,state=snapshot()
    ids={o['task_id']for o in state['starts'].values()};rows=[t for n in current['nodes']for t in n['tasks']if t['task_id']in ids]
    assert len(rows)==len(ids)and 1<=len(ids)<=8
    for r in rows:
        assert r['completed_real_research_receipt']and r['output_complete']and r['commit_confirmed']and r['native_cleanup_complete']and not r['worker_alive'],r['task_id']
        cfg=r['native_thread_configuration'];assert cfg['model']=='gpt-6.1-sol'and cfg['reasoning_effort']in('high','xhigh','max')
        if r['node_id']in{p['root_node_id'],*state['leaders'].values()}:assert cfg['reasoning_effort']=='max'
    assert not[r for r in current['queue']if r['state']=='pending'],'Unconsumed AI continuation: inspect, do not close or replay'
    from yohaku_project_tasks import Tasks
    from yohaku_workflow_gate import gate
    from mechanisms_host import rpc
    taskapi=Tasks(p['world']);programs=[]
    for f in(Path(p['home'])/'.local/state/yohaku/project-tasks/records').glob('*.json'):
        r=json.loads(f.read_bytes())
        if r.get('program_budget',{}).get('model_task')not in ids:continue
        s=taskapi.status(task_id=r['task_id']);receipt=r['receipt'];assert s['status']=='done'and receipt['exit_code']==0 and receipt['cleanup_confirmed']and receipt['output_complete']
        for a in receipt.get('artifacts',[]):assert sha(a['host_path'])==a['sha256']
        programs.append(dict(task_id=r['task_id'],action=r['action'],status=s['status'],source_set=r['snapshot']['source_set'],allocation=r['program_budget']['allocation'],cleanup_confirmed=True,exit_code=0))
    budget=rpc(p['program_budget']['socket'],dict(op='status'));assert not budget['unresolved_leases']
    assert budget['issued']['search']<=2000000 and budget['issued']['verification']<=50000
    assert budget['reported']==dict(search=140329,verification=301),'New work requires another final audit'
    required={('M-538c85aecd32c8d0',2),('M-faadd67bbdf57a62',2),('M-110bcf615851324b',1)}
    assert required.issubset({(e['id'],e['revision'])for e in entries})
    reviews=[e for e in events if e['kind']=='native_tool_completed'and e['data'].get('name')=='math_review'and e['data'].get('result',{}).get('ok')and e['actor'].get('task_id')in ids]
    assert any(e['actor']['actor_node_id']=='ai-node-22a9d6534cbf32a3d7d5029c'and e['data']['arguments']['id']=='M-faadd67bbdf57a62'and e['data']['arguments']['revision']==1 for e in reviews),'Original experiment summary not independently reviewed'
    review_scope=dict(theory_exact_version='M-538c85aecd32c8d0@2',experiment_summary_reviewed_version='M-faadd67bbdf57a62@1',experiment_narrower_revision='M-faadd67bbdf57a62@2',revision2_has_independent_review=False,revision2_change='Only narrows the incomplete forward-depth9/10 claim; no automatic review inheritance',independent_fixed_path_acceptance='M-110bcf615851324b@1',search_or_reverse_dictionary_independently_rerun=False)
    g=gate()
    with g.tx()as v:
        assert v['policy_sha256']==state['policy_sha256']and len(v['starts'])==len(ids)
        if v.get('phase')!='closed':
            assert not v.get('shared_stop')
            v['shared_stop']=dict(reason='Finite user round completed after independent acceptance; future admission closed',at=time.time(),new_dispatch_allowed=False,completed_goal_id=PHASE)
            v['phase']='closed';g.event(v,'finite_stage_completed_and_closed',model_attempts=len(ids),model_turns=len(v['turns']),program_tasks=programs,program_budget=budget,new_authority_added=False)
    out=dict(at=time.time(),asia_shanghai=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(),goal_id=PHASE,status='complete_with_theory_result_and_finite_search_negative',model_attempts=len(ids),model_turns=len(state['turns']),remaining_unused_turns=8-len(ids),all_models_done_committed_and_clean=True,tasks=[{k:r[k]for k in('node_id','task_id','status','thread_id','turn_id','requested_profile','native_thread_configuration','completed_real_research_receipt')}for r in rows],first_admission_at=state['first_admission_at'],absolute_deadline=state['first_send_at']+5400,completed_before_deadline=time.time()<state['first_send_at']+5400,programs=programs,program_budget=budget,pending_model_tasks=0,pending_program_tasks=0,pending_ai_continuations=0,admission_closed=True,old_stops_failures_memories_and_authorities_preserved=True,old_unused_two_reused=False,competition_platform_upload=False,leaderboard_read=False,publication_status='pending_host_github_write_and_readback')
    out['independent_review_scope']=review_scope
    save(BASE/'FINAL-LOCAL-STATUS.json',out);snapshot();print(json.dumps({k:out[k]for k in('status','model_turns','remaining_unused_turns','programs','admission_closed','publication_status')},ensure_ascii=False))
if __name__=='__main__':main()
