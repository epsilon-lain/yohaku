"""Observe this delta phase; consume only AI-authored native continuations."""
import argparse,datetime,fcntl,hashlib,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
from zoneinfo import ZoneInfo
from supplement import BASE,ORIGINAL,PHASE,activate,verify_parent,save,sha

def inspect_project(project,row):
    try:
        st=project.status(request_id=row['request_id']);record=project._owned(st['task_id'])
        return {'native_submit':row,'status':st,'private_record':record}
    except Exception as exc:
        return {'native_submit':row,'inspection_error':str(exc),'inspection_error_type':type(exc).__name__,'original_identity_only':True,'request_not_replayed':True}

def observe():
    verify_parent();p=activate()
    from manage_native import snapshot
    from yohaku_project_tasks import Tasks
    from yohaku_experiment_groups import Groups
    data=snapshot(BASE);allstatus,events,entries,state=data
    before=json.loads((BASE/'BEFORE.json').read_bytes());operations={v['task_id']:v for v in state['starts'].values()}
    tasks=[];nodes=[]
    for node in allstatus['nodes']:
        for task in node['tasks']:
            if task['task_id']not in operations:continue
            op=operations[task['task_id']]
            tasks.append(dict(task,native_node_role=node['role'],original_node_id=node['node_id'],dispatch_origin='user_directed'if op['submitted_by']=='main'else'ai_native_dispatch',assigned_task=op['exact_input']['task'],source_binding=op.get('source_binding')))
        if any(t['node_id']==node['node_id']for t in tasks):nodes.append({k:node[k]for k in('node_id','role','created_by','profile','memory_source','project_scopes')})
    newids=set(operations);project=Tasks(p['world']);projects=[]
    for row in Groups(p['world']).status(p['group_id']).get('project_requests',{}).values():
        if row['model_task_id']not in newids:continue
        # Local preflight/record gaps remain observations, not global failures.
        projects.append(inspect_project(project,row))
    newevents=[e for e in events if e['seq']>before['knowledge_prefix']]
    native=[t for t in tasks if t.get('turn_id')];complete=[t for t in tasks if t.get('completed_real_research_receipt')]
    directions={team:{'node_id':nid,'tasks':[{'task_id':t['task_id'],'status':t['status'],'native_state':t.get('native_state'),'turn_id':t.get('turn_id'),'completed_real_research_receipt':t.get('completed_real_research_receipt'),'assigned_task':t.get('assigned_task')}for t in tasks if t['node_id']==nid]}for team,nid in state['leaders'].items()}
    classification='actual_native_inference_running'if any(t['status']=='running'and t.get('turn_id')for t in tasks)else'completed_native_tasks'if complete else'dispatched_not_inference_confirmed'if tasks else'prepared_not_dispatched'
    out={'round_id':PHASE,'observed_at':time.time(),'observed_at_asia_shanghai':datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),'classification':classification,'baseline_knowledge_prefix':before['knowledge_prefix'],'knowledge_event_prefix':allstatus['knowledge_event_prefix'],'gate_event_prefix':allstatus['gate_event_prefix'],'original_run_id':p['experiment_id'],'original_root_node_id':p['root_node_id'],'new_nodes':nodes,'tasks':tasks,'directions':directions,'project_receipts':projects,'new_math_entries':[e for e in entries if e.get('source_task')in newids],'external_source_reads':[e for e in newevents if e['kind']in('math_body_read','actual_read')],'adoption_claims':[e for e in newevents if e['kind']=='math_adopt'],'ai_continuation_requests':[e for e in newevents if e['kind']=='continuation_requested'],'consumed_ai_continuations':[e for e in newevents if e['kind']=='explicit_ai_continuation_consumed'],'tool_failures_retained':[e for e in newevents if e['kind']=='native_tool_completed'and not e['data']['result'].get('ok')],'resource_status':allstatus['gate_status'],'original_policy_sha256':before['parent_pins'][0]['sha256'],'old_policy_unchanged':True,'old_stop_and_state_unchanged':True,'stage_reset':False,'supervisor':allstatus.get('supervisor'),'platform_upload':False,'original_record_count':len(before['prior_task_ids']),'new_native_task_count':len(tasks)}
    save(BASE/'ROUND-STATUS.json',out);save(BASE/'ROUND-EVENTS.json',newevents)
    lines=['Yohaku 概念转换研究增补：实际接续进展',out['observed_at_asia_shanghai'],classification,'用户指令事件968；独立追加阶段，旧phase/state/shared_stop及责任不改。','所有研究只Sol，原三负责人max。准备、派发、原生turn确认、真实计算和完成分别记录。','']
    for t in tasks:lines+=['角色：'+t['native_node_role'],'node='+t['node_id'],'model task='+t['task_id']+' / '+t['status'],'thread='+str(t.get('thread_id'))+' / turn='+str(t.get('turn_id')),'请求='+json.dumps(t['requested_profile'],ensure_ascii=False),'原生回读='+json.dumps(t.get('native_thread_configuration'),ensure_ascii=False),'完整真实完成回执='+str(t.get('completed_real_research_receipt')),'实际分配题目：'+t.get('assigned_task',''),'']
    lines+=['实际project计算数量='+str(len(projects)),'新数学精确版本='+str([(e['id'],e['revision'],e['title'])for e in out['new_math_entries']]),'门禁='+json.dumps(out['resource_status'],ensure_ascii=False),'完整结构化回执：ROUND-STATUS.json；原事件：ROUND-EVENTS.json。','公开结果只在实际完成/负结果后整理；不会把本外部任务包或零推理自检算研究。']
    (BASE/'中文进展.txt').write_text('\n'.join(lines)+'\n')
    return out,data

def compact(out):
    return {'phase':PHASE,'classification':out['classification'],'knowledge_prefix':out['knowledge_event_prefix'],'tasks':[{'node_id':t['node_id'],'role':t['native_node_role'],'task_id':t['task_id'],'status':t['status'],'turn_id':t.get('turn_id'),'native_state':t.get('native_state'),'complete':t.get('completed_real_research_receipt'),'error':t.get('error')}for t in out['tasks']],'projects':[{'task_id':r.get('status',{}).get('task_id'),'status':r.get('status',{}).get('status'),'action':r.get('status',{}).get('action'),'inspection_error':r.get('inspection_error'),'request_id':r['native_submit']['request_id']}for r in out['project_receipts']],'math_entries':[{'id':m['id'],'revision':m['revision'],'title':m['title']}for m in out['new_math_entries']],'gate_status':out['resource_status']}

def continuation_profile(node,limits):
    # Node-creation budgets predate the supplement. Preserve model/effort while
    # bounding resources to the current phase; never choose a weaker model.
    tasks=node.get('tasks',[])
    old=(tasks[-1].get('requested_profile')if tasks else None)or node['profile']
    chosen=json.loads(json.dumps(old));budget=chosen['budget']
    budget['timeout_seconds']=min(budget['timeout_seconds'],limits['task_seconds'])
    budget['max_tool_calls']=min(budget['max_tool_calls'],limits['task_tools'])
    return chosen

def consume_ai_queue(current):
    p=activate()
    from yohaku_workflow_gate import gate,GateStopped
    from yohaku_native_research_runtime import service
    from yohaku_ai_nodes import Control
    g=gate();k=service(g)
    if g.shared_stop_status()or Path(p['stop_file']).exists():return
    by_id={n['node_id']:n for n in current['nodes']}
    with k.tx()as db:
        pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'ORDER BY id")]
        requests=[dict(r)for r in db.execute("SELECT * FROM events WHERE kind='continuation_requested'ORDER BY seq")]
    for row in pending:
        target=by_id.get(row['target'])
        if not target:continue
        last=target['tasks'][-1]if target['tasks']else None
        if last and not(last.get('output_complete')and last.get('commit_confirmed')and last.get('native_cleanup_complete')):continue
        source=next((json.loads(e['actor'])for e in requests if json.loads(e['actor']).get('actor_node_id')==row['actor']and json.loads(e['data']).get('request_id')==row['request_id']),None)
        with g.tx()as state:op=next((o for o in state['starts'].values()if o['task_id']==(source or{}).get('task_id')),None)
        if not op:continue # retained predecessor intents require an explicit bridge
        profile=continuation_profile(target,p['limits']);g.cached_profile(profile)
        request='continue-'+hashlib.sha256((row['actor']+'\0'+row['request_id']).encode()).hexdigest()[:32]
        try:result=Control(p['world'],actor=row['actor'],workflow_context=g.binding(op)).node_dispatch(row['target'],request,row['task'],profile=profile,_workflow_route='continuation')
        except GateStopped as exc:
            k.record({'actor_node_id':'HOST'},'continuation_admission_blocked',{'queue_id':row['id'],'request_id':request,'error':str(exc),'profile':profile});return
        except Exception as exc:
            k.record({'actor_node_id':'HOST'},'continuation_original_outcome_requires_inspection',{'queue_id':row['id'],'request_id':request,'error':str(exc),'profile':profile});g.request_shared_stop('Continuation dispatch requires original-ID inspection',{'queue_id':row['id'],'request_id':request,'error':str(exc)});return
        with k.tx()as db:
            db.execute("UPDATE queue SET state='dispatched'WHERE id=?",(row['id'],));k.event(db,{'actor_node_id':'HOST'},'explicit_ai_continuation_consumed',{'queue_id':row['id'],'source_actor_task':source,'request_id':request,'result':result,'effective_profile':profile,'host_selected_mathematical_task':False})

def serve():
    p=activate();from yohaku_codex_tasks import identity
    from yohaku_workflow_gate import gate
    fd=os.open(BASE/'supervisor.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    save(BASE/'SUPERVISOR.json',{'identity':identity(os.getpid()),'at':time.time(),'status':'observing_delta_phase_only','continuation':'actual research_continue only','original_phase_stop_not_cleared':True})
    def drain(sig,*args):gate().request_shared_stop('Supplement observer signal; drain new admission only',{'signal':sig})
    signal.signal(signal.SIGTERM,drain);signal.signal(signal.SIGINT,drain)
    while True:
        try:
            out,_=observe()
            consume_ai_queue(json.loads((BASE/'CURRENT.json').read_bytes()))
        except Exception as exc:
            save(BASE/'SUPERVISOR-ERROR.json',{'at':time.time(),'error':str(exc),'traceback':traceback.format_exc(),'no_replay':True})
            try:gate().request_shared_stop('Supplement observer requires inspection',{'error':str(exc)})
            except Exception:pass
        time.sleep(8)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['status','serve','start']);args=parser.parse_args()
    if args.action=='serve':serve()
    elif args.action=='status':print(json.dumps(compact(observe()[0]),ensure_ascii=False))
    else:
        p=activate();from yohaku_codex_tasks import identity
        saved=json.loads((BASE/'SUPERVISOR.json').read_bytes())if(BASE/'SUPERVISOR.json').exists()else{}
        old=saved.get('identity')or{};live=identity(old.get('pid'))
        if live and live['start']==old['start']and live['state']not in('Z','X'):raise RuntimeError('Original supplement supervisor already active; no duplicate')
        with(BASE/'supervisor.log').open('ab')as log:child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'serve'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,cwd=BASE)
        print(json.dumps({'observer_pid':child.pid,'starts_model':False,'consumes_only_AI_requests':True}))
