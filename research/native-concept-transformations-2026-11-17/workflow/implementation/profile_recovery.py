"""Add a delta recovery phase after a verified clean boundary; no stop reset."""
import copy,json,os,re,shutil,signal,sqlite3,sys,time
from pathlib import Path
from supplement import BASE,ORIGINAL,PHASE,activate,verify_parent,save,sha
NEXT=BASE.parent/'native-concept-transformations-20261117-03'
NEXT_PHASE='native-concept-transformations-sol-20261117-03'
REQUEST='user-concept-transformations-20261117-profile-recovery-v1'

def prepare():
    if(NEXT/'POLICY.json').exists():raise RuntimeError('Recovery already prepared; do not reset')
    p=activate();verify_parent()
    from observe import observe
    from yohaku_codex_tasks import identity
    out,data=observe();current,events,entries,state=data
    if not state.get('shared_stop')or state['shared_stop']['reason']!='Continuation dispatch requires original-ID inspection':raise RuntimeError('Unexpected stop needs independent inspection')
    failure=state['shared_stop']['evidence']
    if failure.get('error')!='Worker resource profile exceeds native envelope':raise RuntimeError('Not the inspected local profile failure')
    root=next(n for n in current['nodes']if n['node_id']==p['root_node_id'])
    if any(t['node_request_id']==failure['request_id']for t in root['tasks'])or any(o['operation_id'].endswith(':'+failure['request_id'])for o in state['starts'].values()):raise RuntimeError('Rejected continuation unexpectedly has a native reservation; inspect original ID')
    save(BASE/'CONTINUATION-REJECTION-INSPECTION.json',{'at':time.time(),'request_id':failure['request_id'],'queue_id':failure['queue_id'],'local_error':failure['error'],'node_creation_budget':root['profile']['budget'],'current_limits':p['limits'],'native_node_or_gate_reservation_exists':False,'new_model_started':False,'request_replayed':False,'evidence':'Unchanged Control.node_dispatch validates chosen profile before workflow.reserve_start and Tasks.start. Native default node budget1800 exceeds phase900; no original request registered.'})
    if not out['tasks']or any(t['status']not in('done','error','cancelled')or not t['output_complete']or not t['commit_confirmed']or not t['native_cleanup_complete']or t['worker_alive']for t in out['tasks']):raise RuntimeError('Current original tasks are still in flight; safe boundary not reached')
    if any(r.get('status',{}).get('status')in('running','starting','stopping')for r in out['project_receipts']):raise RuntimeError('Original project still active')
    if any(r['state']in('reserved','attempting','started')for r in state['turns'].values()):raise RuntimeError('Original native transport still active')
    errors=[t for t in out['tasks']if t['status']=='error']
    for t in errors:
        query=json.loads((BASE/'FAILED-TURN-QUERY.json').read_bytes())
        if t['node_id']!=p['root_node_id']or query['task_id']!=t['task_id']or not query['query_ok']or query['native_status']!='interrupted':raise RuntimeError('New model error has not been resolved by original-turn inspection')
    # Retire the old cached observer at a lock-free point; only its own process.
    old=json.loads((BASE/'SUPERVISOR.json').read_bytes())['identity'];live=identity(old['pid'])
    if not live or live['start']!=old['start']:raise RuntimeError('Observer identity differs')
    pid=old['pid'];paused=False
    def locks():return [l for l in Path('/proc/locks').read_text().splitlines()if re.search(r'\b(?:FLOCK|POSIX)\s+ADVISORY\s+\w+\s+'+str(pid)+r'\s',l)and'->'not in l]
    for _ in range(1000):
        if len(locks())<=1:
            os.kill(pid,signal.SIGSTOP);time.sleep(.004)
            fds=[]
            for f in(Path('/proc')/str(pid)/'fd').glob('*'):
                try:fds.append(str(f.resolve()))
                except OSError:pass
            if len(locks())<=1 and not any(f.endswith('.lock')and not f.endswith('/supervisor.lock')for f in fds):paused=True;break
            os.kill(pid,signal.SIGCONT)
        time.sleep(.005)
    if not paused:os.kill(pid,signal.SIGCONT);raise RuntimeError('Observer not lock-free')
    # Capture all old stop bytes after no writer remains.
    before=json.loads((BASE/'BEFORE.json').read_bytes());pins=before['parent_pins']+[{'path':str(BASE/name),'sha256':sha(BASE/name)}for name in('POLICY.json','STATE.json')]
    remaining=p['limits']['turns']-len(state['turns']);deadline=state['first_send_at']+p['limits']['seconds']
    if remaining<3 or deadline-time.time()<900:raise RuntimeError('Insufficient remaining original supplement envelope')
    dest=NEXT/'preserved-predecessor';dest.mkdir()
    for name in('POLICY.json','STATE.json','ROUND-STATUS.json','ROUND-EVENTS.json','CURRENT.json','COMPLETE-RECEIPTS.json','SUPERVISOR-ERROR.json','OBSERVER-REPAIR-NOTICE.json'):
        if(BASE/name).exists():shutil.copy2(BASE/name,dest/name)
    db=sqlite3.connect(p['knowledge_db']);db.row_factory=sqlite3.Row
    pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'")]
    db.backup(sqlite3.connect(str(dest/'knowledge.sqlite3')));db.close()
    # Existing explicit AI intents remain recorded, but are not sent through a
    # foreign phase binding. The new user-recovery root will read and resolve.
    from yohaku_native_research_runtime import service
    k=service()
    with k.tx()as db:
        for row in pending:
            db.execute("UPDATE queue SET state='carried_to_recovery'WHERE id=?AND state='pending'",(row['id'],))
        transfer=k.event(db,{'actor_node_id':'HOST','source':'same_user_instruction_recovery'},'user_instruction_recovery_handoff',{'original_user_event':968,'from_phase':PHASE,'to_phase':NEXT_PHASE,'cause':'continuation adapter inherited legacy1800sec node profile instead of current900sec ceiling; rejected locally before native reservation','stop_preserved':state['shared_stop'],'pending_ai_intents_carried_not_dispatched':pending,'remaining_native_turns':remaining,'original_deadline':deadline,'new_mathematical_goal':False})
    for name in('supplement.py','observe.py','verify_bridge.py','collect_public.py','public_reproduce.py','aggregate.py'):
        raw=(BASE/name).read_text()
        if name=='supplement.py':raw=re.sub(r"^PHASE=.*$","PHASE='"+NEXT_PHASE+"'",raw,flags=re.M)
        (NEXT/name).write_text(raw)
    shutil.copytree(BASE/'external',NEXT/'external');shutil.copy2(BASE/'IMPORT.json',NEXT/'IMPORT.json');shutil.copy2(BASE/'ACTUAL-CATALOG.json',NEXT/'ACTUAL-CATALOG.json');shutil.copy2(BASE/'PARENT-TURN-QUERY.json',NEXT/'PARENT-TURN-QUERY.json');shutil.copy2(BASE/'PREDECESSOR-TIMEOUT-QUERY.json',NEXT/'PREDECESSOR-TIMEOUT-QUERY.json')
    total=p['lineage']['total_user_supplement_turn_ceiling'];used=p['lineage']['previous_delta_turns_reserved']+len(state['turns'])
    assert remaining+used==total
    q=copy.deepcopy(p);q.update(experiment_id=NEXT_PHASE,state_path=str(NEXT/'STATE.json'),stop_file=str(NEXT/'DRAIN'),catalog_path=str(NEXT/'ACTUAL-CATALOG.json'),authorization='Same explicit user event968; local continuation-profile repair. No new funds, native turn budget or deadline.',lineage={'parent_pins':pins,'original_user_event':968,'previous_delta_phase':PHASE,'previous_delta_turns_reserved':used,'total_user_supplement_turn_ceiling':total,'deadline_inherited_exactly':deadline,'old_stops_preserved':True})
    q['limits']['turns']=remaining
    save(NEXT/'POLICY.json',q)
    v={'policy_sha256':sha(NEXT/'POLICY.json'),'phase':'open','members':state['members'],'starts':{},'turns':{},'leaders':state['leaders'],'events':[{'seq':1,'at':time.time(),'kind':'same_user_authority_recovery_bridge','parent_pins':pins,'handoff_event':transfer,'old_stops_preserved':True,'native_turns_remaining':remaining,'deadline_inherited':deadline}],'shared_stop':None,'first_send_at':state['first_send_at'],'parent_liability_reference':q['lineage']}
    save(NEXT/'STATE.json',v)
    save(NEXT/'BEFORE.json',{'at':time.time(),'knowledge_prefix':transfer,'gate_prefix':len(state['events']),'parent_pins':pins,'original_policy':p,'original_state':state,'prior_task_ids':before['prior_task_ids']+[t['task_id']for t in out['tasks']],'prior_native_receipts':current['nodes'],'old_observer_before':old,'old_observer_after':identity(pid),'pending_ai_intents_carried':pending,'first_user_phase_path':before.get('first_user_phase_path',str(BASE)),'original_user_event':968,'old_budget_reset':False,'same_deadline':deadline})
    save(NEXT/'REGISTRATION.json',{'native_run_id':NEXT_PHASE,'status':'prepared_not_dispatched','root_node_id':q['root_node_id'],'original_nodes_preserved':True,'new_nodes_created':0,'new_turns_authorized':0,'remaining_prior_user_authority':remaining,'original_deadline':deadline,'predecessor_stop_cleared':False})
    save(BASE/'RECOVERY-BRIDGE.json',{'path':str(NEXT),'phase':NEXT_PHASE,'parent_pins':pins,'handoff_event':transfer,'remaining_turns':remaining,'deadline':deadline,'paused_observer_lock_free':True,'old_stop_cleared':False,'new_budget_granted':False})
    print(json.dumps({'prepared':True,'phase':NEXT_PHASE,'remaining_turns':remaining,'deadline':deadline,'current_tasks_clean':True,'pending_ai_intents':len(pending),'parent_stops_preserved':True}))

def dispatch():
    # No prepared or rejected original task identity is reused.
    sys.path.insert(0,str(NEXT));os.environ['YOHAKU_WORKFLOW_POLICY']=str(NEXT/'POLICY.json')
    from prepare_native import activate as act
    q=act(NEXT)
    from yohaku_ai_nodes import Control
    from yohaku_workflow_gate import gate
    from yohaku_native_research_runtime import service
    for pin in q['lineage']['parent_pins']:
        if sha(pin['path'])!=pin['sha256']:raise RuntimeError('Pinned predecessor changed')
    if not json.loads((NEXT/'ENGINEERING-VALIDATION.json').read_bytes())['passed']:raise RuntimeError('Corrected observer/gate fixture not validated')
    ctrl=Control(q['world']);node=next(n for n in ctrl.node_list()['nodes']if n['node_id']==q['root_node_id']);prior=next((t for t in node['tasks']if t['request_id']==REQUEST),None)
    if prior:
        result=ctrl.node_status(q['root_node_id'],REQUEST);print(json.dumps({'original_task_id':prior['task_id'],'status':result['status'],'replayed':False}));return
    task='同一用户event968的安全恢复交接；不是新数学目标，也不是AI自发续题。'+(NEXT/'external/task/CODEX_TASK.md').read_text()
    task+='\n\n宿主接续工程修复：父阶段02的自动续行使用了node创建时的1800秒默认profile，超过阶段900秒，已在native reservation及模型启动前被拒绝。原请求continue-d637079e69fc161c056a4746b87a0251已查无node/gate原生reservation，未启动模型，旧拒绝/stop/队列责任全保留。新观察器已改为显式传当前合规profile并裁定预算上限，不更换模型/effort。父阶段02三模型均done/commit/cleanup确认。现在独立恢复桥 '+NEXT_PHASE+'，原3小时截止及总12turn上限不变（先前6turn已占用，余'+str(q['limits']['turns'])+'）；全部父阶段policy/STATE保持SHA固定。\n'
    task+='本次用户目标中的理论补充、商图有限核验及同伴限域审阅均已完成：pair任务project-task-8af630bd59010ae18cf545ad37f18415；商图任务project-task-24e34a0dde1b1bd250763d7a99875d52；新M-57835ea93dc9d121@1及review1841。不重算这些或普通8/13/Stable08491=10。当前唯一实践缺口是原应用07445冻结搜索从未真正运行。请接续原head和原冻结程序，自己决定最小恢复/交付边界，先促成真实项目task及官方验收；不要为流程再增员或重开已完理论。所有研究只Sol，负责人max，单任务900秒96工具。\n'
    task+='应用两个旧ID app-r3-07445-target-info-beam-v1、app-r3-07445-target-info-delayed-v2均已记录GateStopped且无task记录；不能重放。新桥允许原负责人基于相同已封存源/协议重新plan并以新的请求ID提交延迟执行，保持原失败和冻结哈希。先核查原ID，不把lookup-derived task_id当实际运行。你的原商图计算已经真正完成，勿再次恢复它。\n'
    task+='用户仍要求实际推进，不停留于派发；宿主会按真实回执公开数学、程序与过程。原HOST通知若未读，不推定已采用。早存检查点、独立复核明确范围；最后给中文可公开稿/过程索引及当前合法提交文件，不上传平台。'
    task+=' 当前root前一任务已成功finish。请继续采用其小检查点方式，不为等待应用模型而挂住当前任务；如原AI续题的终态对账需待应用结束，可先保存/finish，再用新的明确research_continue请求留精确核验。自动续行现会显式保持Sol/max900/96，不再继承旧1800秒默认值。'
    before=json.loads((NEXT/'BEFORE.json').read_bytes())
    if before['pending_ai_intents_carried']:task+='\n原生AI在旧任务实际提出的续行意图（保留旧队列行、不假称已派发）：'+json.dumps(before['pending_ai_intents_carried'],ensure_ascii=False)
    prompt=NEXT/'ROOT-REQUEST.txt'
    if prompt.exists():raise RuntimeError('Recovery request prepared; inspect registry before any send')
    prompt.write_text(task)
    result=ctrl.node_dispatch(q['root_node_id'],REQUEST,task,profile={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}})
    save(NEXT/'USER-DISPATCH.json',{'request_id':REQUEST,'kind':'user_directed_recovery_same_goal','original_user_event':968,'prompt_sha256':sha(prompt),'result':result,'at':time.time()})
    service().record({'actor_node_id':'HOST','source':'same_user_instruction_recovery'},'user_instruction_recovery_dispatched',{'request_id':REQUEST,'original_user_event':968,'prompt_sha256':sha(prompt),'result':result,'new_goal':False,'not_AI_continuation':True})
    print(json.dumps({'task_id':result['task_id'],'status':result['status'],'same_user_goal':True,'budget_or_deadline_renewed':False}))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['prepare','dispatch']);args=parser.parse_args();{'prepare':prepare,'dispatch':dispatch}[args.action]()

