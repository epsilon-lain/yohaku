"""Add a delta recovery phase after a verified clean boundary; no stop reset."""
import copy,json,os,re,shutil,signal,sqlite3,sys,time
from pathlib import Path
from supplement import BASE,ORIGINAL,PHASE,activate,verify_parent,save,sha
NEXT=BASE.parent/'native-concept-transformations-20261117-02'
NEXT_PHASE='native-concept-transformations-sol-20261117-02'
REQUEST='user-concept-transformations-20261117-recovery-v1'

def prepare():
    if(NEXT/'POLICY.json').exists():raise RuntimeError('Recovery already prepared; do not reset')
    p=activate();verify_parent()
    from observe import observe
    from yohaku_codex_tasks import identity
    out,data=observe();current,events,entries,state=data
    if not state.get('shared_stop')or state['shared_stop']['reason']not in('Supplement observer requires inspection','Original native task failed; inspect before new admission'):raise RuntimeError('Unexpected stop needs independent inspection')
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
        transfer=k.event(db,{'actor_node_id':'HOST','source':'same_user_instruction_recovery'},'user_instruction_recovery_handoff',{'original_user_event':968,'from_phase':PHASE,'to_phase':NEXT_PHASE,'cause':'observer misclassified a local preflight/record gap as a phase failure','stop_preserved':state['shared_stop'],'pending_ai_intents_carried_not_dispatched':pending,'remaining_native_turns':remaining,'original_deadline':deadline,'new_mathematical_goal':False})
    for name in('supplement.py','observe.py','verify_bridge.py','collect_public.py','public_reproduce.py'):
        raw=(BASE/name).read_text()
        if name=='supplement.py':raw=raw.replace("PHASE='native-concept-transformations-sol-20261117-01'","PHASE='native-concept-transformations-sol-20261117-02'")
        (NEXT/name).write_text(raw)
    shutil.copytree(BASE/'external',NEXT/'external');shutil.copy2(BASE/'IMPORT.json',NEXT/'IMPORT.json');shutil.copy2(BASE/'ACTUAL-CATALOG.json',NEXT/'ACTUAL-CATALOG.json');shutil.copy2(BASE/'PARENT-TURN-QUERY.json',NEXT/'PARENT-TURN-QUERY.json');shutil.copy2(BASE/'FAILED-TURN-QUERY.json',NEXT/'PREDECESSOR-TIMEOUT-QUERY.json')
    q=copy.deepcopy(p);q.update(experiment_id=NEXT_PHASE,state_path=str(NEXT/'STATE.json'),stop_file=str(NEXT/'DRAIN'),catalog_path=str(NEXT/'ACTUAL-CATALOG.json'),authorization='Same explicit user instruction event968; bounded repair of host observer error. No new funds, turn budget, or deadline.',lineage={'parent_pins':pins,'original_user_event':968,'previous_delta_phase':PHASE,'previous_delta_turns_reserved':len(state['turns']),'total_user_supplement_turn_ceiling':p['limits']['turns'],'deadline_inherited_exactly':deadline,'old_stops_preserved':True})
    q['limits']['turns']=remaining
    save(NEXT/'POLICY.json',q)
    v={'policy_sha256':sha(NEXT/'POLICY.json'),'phase':'open','members':state['members'],'starts':{},'turns':{},'leaders':state['leaders'],'events':[{'seq':1,'at':time.time(),'kind':'same_user_authority_recovery_bridge','parent_pins':pins,'handoff_event':transfer,'old_stops_preserved':True,'native_turns_remaining':remaining,'deadline_inherited':deadline}],'shared_stop':None,'first_send_at':state['first_send_at'],'parent_liability_reference':q['lineage']}
    save(NEXT/'STATE.json',v)
    save(NEXT/'BEFORE.json',{'at':time.time(),'knowledge_prefix':transfer,'gate_prefix':len(state['events']),'parent_pins':pins,'original_policy':p,'original_state':state,'prior_task_ids':before['prior_task_ids']+[t['task_id']for t in out['tasks']],'prior_native_receipts':current['nodes'],'old_observer_before':old,'old_observer_after':identity(pid),'pending_ai_intents_carried':pending,'first_user_phase_path':str(BASE),'original_user_event':968,'old_budget_reset':False,'same_deadline':deadline})
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
    task+='\n\n宿主工程修复：前一delta阶段因观察器把已登记但未运行project请求当成故障触发shared_stop。停止记录原样保留；修正后的观察器将此类条目作为inspection_error保留，不关闭全阶段。前一阶段两head均done，root又触900秒限额error；其原turn已只读查为interrupted，三者均commit/cleanup确认，无在途。理论真实核验已完成。root的解析证明和独立审阅已保存，不能把其未运行枚举称完成。现在独立恢复桥 '+NEXT_PHASE+'，仍用本次原3小时截止（first_send_at不重置），剩余'+str(q['limits']['turns'])+'次native turns；不补发已用预算。原两个停止阶段的policy/STATE保持SHA固定。\n'
    task+='请先查原权威记忆、共有数学索引/未完成项和实际旧请求回执；接续你已自选的商图枚举和应用队已冻结的07445 swapped-target/abelianization研究，不强制重算已完成的理论枚举。你自己安排原head、工具和复核/边界；可以让理论负责人独立审稿或自行选原用户目标内的小题。相同理论/应用仍可独立评价。所有新研究只Sol，负责人max、其余>=high；单任务900秒96工具。\n'
    task+='旧root project请求round3-root-quotient-audit-v1为source_conflict、replanned-v2明确GateStopped，应用旧submit同样GateStopped，均没有执行；请核查原ID并保留它们，不重放原request，不覆盖原source/冻结协议/失败。已知确定未启动后，修复接口下可用新请求ID和新的plan提交原封存程序，记录延迟执行与原冻结版本关系；未知ID只能查询。原理论project-task-8af630bd59010ae18cf545ad37f18415已done，无需重复。\n'
    task+='用户仍要求实际推进，不停留于派发；宿主会按真实回执公开数学、程序与过程。原HOST通知若未读，不推定已采用。早存检查点、独立复核明确范围；最后给中文可公开稿/过程索引及当前合法提交文件，不上传平台。'
    task+=' root已连续两次长收尾触时限：本任务重点是已选程序的真实恢复与应用接续，不用再全面重读旧研究或扩展新数学主线。你自行把工作切成能尽早保存/finish的小交付；别为等待另一模型完成而保持本任务。需要后续复核应先保存当前成果，再以research_continue提出精确小题，宿主按实际剩余授权消费。'
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

