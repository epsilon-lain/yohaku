"""Consume an existing AI closure request under the SAME six-turn grant."""
import hashlib,json,os,sqlite3,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
PREVIOUS=BASE.parent/'operation-universes-continuation-20261117-01'
ORIGINAL=BASE.parent/'native-two-team-sol-20261116'
LITERATURE=BASE.parent/'operation-universes-literature-20261117'
PHASE='operation-universes-native-sol-20261117-02'
sys.path.insert(0,str(ORIGINAL))
from prepare_native import activate as original_activate,save,sha,CANDIDATE
def activate():return original_activate(BASE)
def verify_parent():
    b=json.loads((BASE/'BEFORE.json').read_bytes())
    for r in b['parent_pins']:
        if sha(r['path'])!=r['sha256']:raise RuntimeError('Retained authority changed: '+r['path'])
    return b

def prepare():
    if(BASE/'POLICY.json').exists():raise RuntimeError('Recovery already exists: no reset')
    p=original_activate(PREVIOUS)
    from manage_native import snapshot,verify_candidate
    from yohaku_codex_tasks import identity,read_record,alive
    verify_candidate();current,events,entries,state=snapshot(PREVIOUS)
    original=json.loads((PREVIOUS/'BEFORE.json').read_bytes());queries=json.loads((PREVIOUS/'FAILED-TURN-QUERIES.json').read_bytes())
    own={o['task_id']for o in state['starts'].values()}
    for n in current['nodes']:
        for t in n['tasks']:
            r=read_record(t['task_id'])
            if not(t['output_complete']and r['commit_confirmed']and(r.get('receipt')or{}).get('native_cleanup_complete'))or alive(r):raise RuntimeError('Task not terminal/clean: '+t['task_id'])
            if t['task_id']in own and t['status']=='error'and not any(q['task_id']==t['task_id']and q['native_status']=='interrupted'for q in queries['results']):raise RuntimeError('Original failed turn not resolved')
    obs=json.loads((PREVIOUS/'OBSERVER-IDLE-PAUSE.json').read_bytes())['identity'];live=identity(obs['pid'])
    if not live or live['start']!=obs['start']or live['state']!='T':raise RuntimeError('Parent observer not safely paused')
    charged=len(state['turns']);remaining=p['limits']['turns']-charged
    if charged!=3 or remaining!=3 or not state['shared_stop']or time.time()>=state['first_send_at']+5400:raise RuntimeError('Remaining SAME user authority differs')
    db=sqlite3.connect(p['knowledge_db']);db.row_factory=sqlite3.Row
    pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'")]
    if len(pending)!=1:raise RuntimeError('Expected exact original AI continuation only')
    q=pending[0];source=next(e for e in events if e['kind']=='continuation_requested'and e['actor'].get('task_id')in own and e['data']['request_id']==q['request_id']and e['actor']['actor_node_id']==q['actor'])
    if q['target']!=p['root_node_id']or q['actor']!=p['root_node_id']:raise RuntimeError('Original coordinator closure differs')
    db.backup(sqlite3.connect(str(BASE/'knowledge-before.private.sqlite3')));db.close()
    pins=original['parent_pins']+[dict(path=str(PREVIOUS/n),sha256=sha(PREVIOUS/n))for n in('POLICY.json','STATE.json')]
    save(BASE/'BEFORE.json',dict(at=time.time(),knowledge_prefix=current['knowledge_event_prefix'],parent_pins=pins,
        original_policy=p,original_state=state,prior_task_ids=[t['task_id']for n in current['nodes']for t in n['tasks']],
        source_ai_continuation=source,pending_original=q,same_grant_charged=charged,same_grant_remaining=remaining,
        exact_deadline=state['first_send_at']+5400,old_stops_preserved=True,extra_turns_or_time_added=False))
    (BASE/'ACTUAL-CATALOG.json').write_bytes((PREVIOUS/'ACTUAL-CATALOG.json').read_bytes())
    p.update(experiment_id=PHASE,state_path=str(BASE/'STATE.json'),stop_file=str(BASE/'DRAIN'),
        catalog_path=str(BASE/'ACTUAL-CATALOG.json'),catalog_sha256=sha(BASE/'ACTUAL-CATALOG.json'),
        authorization={'kind':'same_user_event2974_remaining_authority_only','original_turn_ceiling':6,'parent_charged':charged,'remaining_ceiling':remaining,'first_admission_at':state['first_admission_at'],'exact_deadline':state['first_send_at']+5400,'new_authority_added':False},
        lineage={'parent_pins':pins,'same_grant_turns_charged':charged,'total_user_grant_turn_ceiling':6,
            'previous_stop':state['shared_stop'],'exact_first_admission':state['first_admission_at'],
            'deadline_inherited_exactly':state['first_send_at']+5400,'source_ai_request_event':source['seq'],'source_queue_id':q['id'],'old_stop_cleared':False})
    p['limits']['turns']=remaining
    p['common_instructions']+=' 本段仅消费同一用户2974已授6回合/90分钟中的剩余3回合，原段900秒收尾超时/stop不变。只消费root已经提出的证据核对请求；不新增搜索/节点。请先在600秒内保存小核对稿，预留最后300秒原生turn收尾；research_finish后立即给简短最终答复，不新增长核对或等待。此处只是资源提醒，不替AI选数学题。'
    save(BASE/'POLICY.json',p)
    v=dict(policy_sha256=sha(BASE/'POLICY.json'),phase='open',members=state['members'],leaders=state['leaders'],starts={},turns={},
        events=[dict(seq=1,at=time.time(),kind='remaining_same_grant_recovery',source_ai_event=source['seq'],parent_pins=pins,parent_charged=charged,remaining=remaining,no_time_or_turns_added=True)],
        shared_stop=None,first_send_at=state['first_send_at'],first_admission_at=state['first_admission_at'],parent_liability_reference=p['lineage'])
    save(BASE/'STATE.json',v)
    (BASE/'observer.py').write_bytes((PREVIOUS/'observer.py').read_bytes())
    from yohaku_workflow_gate import gate
    # Activation must follow the new private pin, not the stopped parent.
    activate();g=gate();g.ensure_admission_open();g.cached_profile({'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}})
    verify_parent();save(BASE/'ENGINEERING-VALIDATION.json',dict(passed=True,remaining_plus_parent_equals_six=charged+remaining==6,exact_deadline_retained=True,old_stops_preserved=True,all_previous_tasks_terminal_and_clean=True,failed_turns_read_by_original_ids=True,actual_model_requests=0))
    print(json.dumps(dict(prepared=True,source_ai_event=source['seq'],remaining=remaining,deadline=v['first_send_at']+5400,new_models=0,new_authority_added=False)))

def dispatch():
    b=verify_parent();p=activate();q=b['pending_original'];source=b['source_ai_continuation']
    from yohaku_ai_nodes import Control
    from yohaku_native_research_runtime import service
    from yohaku_workflow_gate import gate
    request='continue-'+hashlib.sha256((q['actor']+'\0'+q['request_id']).encode()).hexdigest()[:32]
    ctrl=Control(p['world']);root=next(n for n in ctrl.node_list()['nodes']if n['node_id']==p['root_node_id'])
    prior=next((t for t in root['tasks']if t['request_id']==request),None)
    if prior:print(json.dumps(dict(task_id=prior['task_id'],status=ctrl.node_status(p['root_node_id'],request)['status'],replayed=False)));return
    prompt=q['task']+'\n\n宿主只交接你在event3605已明确登记的同一证据核对小任务，不另选数学题。本段仍总2974用户授权最多6回合，前段已占3，本段仅剩3；首准入16:34:54.181718、固定截止18:04:54.181718完全沿用。前段root与theory均900秒收尾超时，原turn都只读查interrupted；应用done、project-task-c0f44bc9f068248f856aa641a7c3aac4 done且清理。前段stop和失败完整保留，不改done。你的原记忆/节点/历史还在。只核必要证据，禁止新搜索/复算/模型；请前600秒保存简短核对稿，留300秒给原生turn收尾。research_finish后立即简短最终回复，不再插入额外工具、长证明或等待。读取旧独立review要保留作者与范围。若还不完整就写明检查范围，不循环补齐。'
    (BASE/'ROOT-REQUEST.txt').write_text(prompt)
    result=ctrl.node_dispatch(p['root_node_id'],request,prompt,profile={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}})
    receipt=dict(at=time.time(),kind='explicit_ai_continuation_consumed_via_inspected_recovery',request_id=request,
        source_user_event=2974,source_ai_event=source['seq'],source_queue_id=q['id'],source_actor_task=source['actor'],
        host_selected_mathematical_task=False,result=result,first_admission_at=p['authorization']['first_admission_at'],
        exact_deadline=b['exact_deadline'],new_time_or_turns_added=False)
    save(BASE/'AI-CONTINUATION-DISPATCH.json',receipt)
    k=service()
    with k.tx()as db:
        row=db.execute('SELECT state FROM queue WHERE id=?',(q['id'],)).fetchone()
        if row['state']!='pending':raise RuntimeError('Original queue state changed: inspect original IDs')
        db.execute("UPDATE queue SET state='dispatched'WHERE id=?",(q['id'],))
        k.event(db,{'actor_node_id':'HOST'},'explicit_ai_continuation_consumed',receipt)
    print(json.dumps(dict(task_id=result['task_id'],request_id=request,status=result['status'],native_confirmation_pending=True,new_authority_added=False)))
if __name__=='__main__':
    {'prepare':prepare,'dispatch':dispatch}[sys.argv[1]]()
