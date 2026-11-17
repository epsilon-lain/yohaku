"""Observe only this grant; consume only its actual AI-authored continuations."""
import argparse,copy,datetime,fcntl,hashlib,json,os,signal,subprocess,sys,time,traceback
from pathlib import Path
from zoneinfo import ZoneInfo
from continuation import BASE,PHASE,activate,verify_parent,save,sha

def observe():
    verify_parent();p=activate()
    from manage_native import snapshot
    from yohaku_experiment_groups import Groups
    from yohaku_project_tasks import Tasks
    allstatus,events,entries,state=snapshot(BASE);b=json.loads((BASE/'BEFORE.json').read_bytes())
    ids={op['task_id']for op in state['starts'].values()};tasks=[]
    for n in allstatus['nodes']:
        for t in n['tasks']:
            if t['task_id']in ids:tasks.append(dict(t,role=n['role']))
    new=[e for e in events if e['seq']>b['knowledge_prefix']];reads=[]
    for e in new:
        if e['kind']!='math_body_read'or e['actor'].get('task_id')not in ids:continue
        d=e['data'];done=next((r for r in new if r['seq']>e['seq']and r['kind']=='native_tool_completed'and r['actor'].get('task_id')==e['actor']['task_id']and r['data']['name']=='math_read'and r['data']['arguments'].get('id')==d['id']),None)
        result=((done or{}).get('data',{}).get('result')or{}).get('result')or{};body=result.get('body','');digest=hashlib.sha256(body.encode()).hexdigest()
        reads.append(dict(event_seq=e['seq'],tool_event_seq=done['seq']if done else None,node_id=e['actor']['actor_node_id'],task_id=e['actor']['task_id'],
            entry_id=d['id'],revision=d['revision'],body_sha256=d['body_sha256'],returned_body_characters=len(body),returned_body_sha256=digest,
            full_body_returned=bool(body and digest==d['body_sha256']),tool_ok=bool(done and done['data']['result'].get('ok')),
            primary_literature=d['id'].startswith('external/mochizuki/')))
    project=Tasks(p['world']);computations=[]
    for r in Groups(p['world']).status(p['group_id']).get('project_requests',{}).values():
        if r['model_task_id']not in ids:continue
        try:computations.append(dict(native_submit=r,status=project.status(request_id=r['request_id'])))
        except Exception as exc:computations.append(dict(native_submit=r,inspection_error=str(exc),original_id_retained=True,replayed=False))
    adoptions=[e for e in new if e['kind']=='math_adopt'and e['actor'].get('task_id')in ids]
    math=[e for e in entries if e.get('source_task')in ids]
    private=dict(at=time.time(),tasks=tasks,new_events=new,new_math=math,reads=reads,computations=computations,state=state)
    save(BASE/'ROUND-PRIVATE.json',private)
    fields=('node_id','role','node_request_id','task_id','submitted_by','status','output_complete','commit_confirmed','native_cleanup_complete','completed_real_research_receipt','requested_profile','native_thread_configuration','thread_id','turn_id','native_state','wire_write_completed','usage','error')
    public=dict(observed_at=time.time(),observed_at_asia_shanghai=datetime.datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(),
        phase=PHASE,knowledge_prefix=allstatus['knowledge_event_prefix'],tasks=[{k:t.get(k)for k in fields}for t in tasks],
        new_grant_limits=p['limits'],gate_status=allstatus['gate_status'],first_admission_at=state.get('first_admission_at'),
        exact_deadline=state['first_send_at']+5400 if state.get('first_send_at')else None,
        parent_authorities_unchanged=True,old_stops_and_liabilities_retained=True,actual_reads=reads,
        adoption_events=[dict(seq=e['seq'],node_id=e['actor']['actor_node_id'],task_id=e['actor']['task_id'],**e['data'])for e in adoptions],
        native_math_versions=[{k:e.get(k)for k in('id','revision','title','summary','source_task','author_node','body_sha256')}for e in math],
        computations=computations,pending_queue=[{k:r[k]for k in('id','actor','target','request_id','state')}for r in allstatus['queue']if r['state']=='pending'],
        tool_failures=[dict(seq=e['seq'],node_id=e['actor']['actor_node_id'],task_id=e['actor']['task_id'],tool=e['data']['name'],error=e['data']['result'].get('error'))for e in new if e['kind']=='native_tool_completed'and e['actor'].get('task_id')in ids and not e['data']['result'].get('ok')],
        full_original_literature_or_private_chat_published=False)
    save(BASE/'STARTUP-AND-PROGRESS.json',public)
    return public,allstatus,events,state

def consume(current,events,state):
    p=activate()
    from yohaku_workflow_gate import gate,GateStopped
    from yohaku_native_research_runtime import service
    from yohaku_ai_nodes import Control
    g=gate();k=service(g)
    if g.shared_stop_status()or Path(p['stop_file']).exists():return
    by_id={n['node_id']:n for n in current['nodes']}
    with k.tx()as db:pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'ORDER BY id")]
    for row in pending:
        target=by_id.get(row['target'])
        if not target:continue
        last=target['tasks'][-1]if target['tasks']else None
        if last and not(last.get('output_complete')and last.get('commit_confirmed')and last.get('native_cleanup_complete')):continue
        source=next((e for e in events if e['kind']=='continuation_requested'and e['actor'].get('actor_node_id')==row['actor']and e['data'].get('request_id')==row['request_id']),None)
        op=next((o for o in state['starts'].values()if o['task_id']==(source or{}).get('actor',{}).get('task_id')),None)
        if not op:continue
        resources=g.status()
        if resources['native_turns_remaining']<=0 or resources['remaining_seconds']<30:return
        old=(last.get('requested_profile')if last else None)or target['profile'];profile=copy.deepcopy(old)
        profile['budget']['timeout_seconds']=min(profile['budget']['timeout_seconds'],900,max(1,int(resources['remaining_seconds'])-5))
        profile['budget']['max_tool_calls']=min(profile['budget']['max_tool_calls'],96);g.cached_profile(profile)
        request='continue-'+hashlib.sha256((row['actor']+'\0'+row['request_id']).encode()).hexdigest()[:32]
        try:result=Control(p['world'],actor=row['actor'],workflow_context=g.binding(op)).node_dispatch(row['target'],request,row['task'],profile=profile,_workflow_route='continuation')
        except GateStopped as exc:
            k.record({'actor_node_id':'HOST'},'continuation_admission_blocked',{'queue_id':row['id'],'request_id':request,'error':str(exc),'profile':profile});return
        except Exception as exc:
            k.record({'actor_node_id':'HOST'},'continuation_original_outcome_requires_inspection',{'queue_id':row['id'],'request_id':request,'error':str(exc)})
            g.request_shared_stop('New-grant continuation needs original-ID inspection',{'queue_id':row['id'],'request_id':request,'error':str(exc)});return
        with k.tx()as db:
            db.execute("UPDATE queue SET state='dispatched'WHERE id=?",(row['id'],))
            k.event(db,{'actor_node_id':'HOST'},'explicit_ai_continuation_consumed',{'queue_id':row['id'],'source_actor_task':source['actor'],'request_id':request,'result':result,'effective_profile':profile,'host_selected_mathematical_task':False})
        return # Observe the admitted worker before considering another request.

def serve():
    p=activate()
    from yohaku_codex_tasks import identity
    from yohaku_workflow_gate import gate
    fd=os.open(BASE/'supervisor.lock',os.O_CREAT|os.O_RDWR,0o600);fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
    save(BASE/'SUPERVISOR.json',{'identity':identity(os.getpid()),'at':time.time(),'status':'new_numeric_grant_observer','consumes_only_ai_requests':True,'old_observers_resumed':False})
    def drain(sig,*args):gate().request_shared_stop('New-grant observer signal; drain admission only',{'signal':sig})
    signal.signal(signal.SIGTERM,drain);signal.signal(signal.SIGINT,drain)
    while True:
        try:
            out,current,events,state=observe();consume(current,events,state)
        except Exception as exc:
            save(BASE/'SUPERVISOR-ERROR.json',{'at':time.time(),'error':str(exc),'traceback':traceback.format_exc(),'no_replay':True})
            gate().request_shared_stop('New observer requires inspection',{'error':str(exc)})
        time.sleep(12)
def compact(x):return dict(observed_at=x['observed_at_asia_shanghai'],tasks=[{k:t[k]for k in('node_id','task_id','status','thread_id','turn_id','native_thread_configuration')}for t in x['tasks']],reads=x['actual_reads'],gate=x['gate_status'],first_admission=x['first_admission_at'],deadline=x['exact_deadline'])
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['status','serve','start']);args=a.parse_args()
    if args.action=='status':print(json.dumps(compact(observe()[0]),ensure_ascii=False))
    elif args.action=='serve':serve()
    else:
        activate();from yohaku_codex_tasks import identity
        if(BASE/'SUPERVISOR.json').exists():
            old=json.loads((BASE/'SUPERVISOR.json').read_bytes())['identity'];live=identity(old['pid'])
            if live and live['start']==old['start']and live['state']not in('Z','X'):raise RuntimeError('Observer already live; no duplicate')
        with(BASE/'observer.log').open('ab')as log:child=subprocess.Popen([sys.executable,'-B',str(Path(__file__).resolve()),'serve'],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True,cwd=BASE)
        print(json.dumps({'observer_pid':child.pid,'new_model_started':False,'old_observers_resumed':False}))
