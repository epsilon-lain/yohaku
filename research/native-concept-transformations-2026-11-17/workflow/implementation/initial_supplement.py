"""Independent user-directed supplement; original phase and nodes are retained."""
import argparse,copy,hashlib,json,os,re,shutil,signal,sqlite3,sys,time,urllib.request
from pathlib import Path
BASE=Path(__file__).resolve().parent
ORIGINAL=BASE.parent/'native-two-team-sol-20261116'
sys.path.insert(0,str(ORIGINAL))
from prepare_native import activate as original_activate,save,sha,CANDIDATE
PHASE='native-concept-transformations-sol-20261117-01'
REQUEST='user-concept-transformations-20261117-v1'
REF='0683661bb89751c6d9d75e6269a77a44b633698e'
REVIEW_REF='0108519169ea786ed186d7c93aa13c33ffac625c'

def activate():
    p=original_activate(BASE)
    return p

def verify_parent():
    b=json.loads((BASE/'BEFORE.json').read_bytes())
    for row in b['parent_pins']:
        if sha(row['path'])!=row['sha256']:raise RuntimeError('Retained parent phase changed: '+row['path'])
    return b

def capture():
    if(BASE/'BEFORE.json').exists():raise RuntimeError('Baseline exists; never reset')
    p=original_activate(ORIGINAL/'run')
    from manage_native import snapshot,verify_candidate
    from yohaku_ai_nodes import Control
    from yohaku_codex_tasks import read_record,alive,identity
    from yohaku_project_tasks import Tasks
    verify_candidate();current,events,entries,state=snapshot(ORIGINAL/'run')
    if not state['shared_stop']:raise RuntimeError('Expected original failure stop must be preserved')
    if state['first_send_at']+p['limits']['seconds']>time.time():raise RuntimeError('Do not silently replace unexpired old authority')
    ctrl=Control(p['world']);taskids=[]
    for n in current['nodes']:
        for t in n['tasks']:
            r=read_record(t['task_id']);receipt=r.get('receipt')or{}
            if not(t.get('output_complete')and r.get('commit_confirmed')and receipt.get('native_cleanup_complete'))or alive(r):raise RuntimeError('Old task not clean terminal: '+t['task_id'])
            for child in r.get('native',[]):
                live=identity(child['pid'])
                if live and str(live['start'])==str(child['start'])and live['state']not in('Z','X'):raise RuntimeError('Original native child alive')
            taskids.append(t['task_id'])
    # All project task records for this world, not just five visible last round.
    records=Path(p['home'])/'.local/state/yohaku/project-tasks/records'
    projects=[];project_service=Tasks(p['world'])
    for file in records.glob('*.json'):
        r=json.loads(file.read_bytes())
        if r.get('world')!=p['world']:continue
        status=project_service.status(task_id=r['task_id']);receipt=status.get('receipt')or{}
        if status['status']not in('done','error','cancelled')or not receipt.get('cleanup_confirmed'):raise RuntimeError('Project task not terminal: '+file.name)
        projects.append({'task_id':r['task_id'],'status':status['status'],'receipt':receipt})
    db=sqlite3.connect('file:'+p['knowledge_db']+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
    pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'")]
    if pending:raise RuntimeError('Existing pending AI task must be resolved by original identity')
    # Pause only the old host observer at a demonstrably lock-free boundary.
    before=current['supervisor']['identity'];pid=before['pid'];live=identity(pid)
    if not live or live['start']!=before['start']:raise RuntimeError('Old observer identity changed')
    def locks():return [l for l in Path('/proc/locks').read_text().splitlines()if re.search(r'\b(?:FLOCK|POSIX)\s+ADVISORY\s+\w+\s+'+str(pid)+r'\s',l)and'->'not in l]
    def fds():
        out=[]
        for f in(Path('/proc')/str(pid)/'fd').glob('*'):
            try:out.append(str(f.resolve()))
            except OSError:pass
        return out
    paused=False
    for attempt in range(1000):
        if len(locks())<=1:
            os.kill(pid,signal.SIGSTOP);time.sleep(.004)
            bad=[f for f in fds()if f.endswith('.lock')and not f.endswith('/supervisor.lock')]
            if len(locks())<=1 and not bad:paused=True;break
            os.kill(pid,signal.SIGCONT)
        time.sleep(.005)
    if not paused:
        os.kill(pid,signal.SIGCONT);raise RuntimeError('Cannot safely pause old observer')
    old=BASE/'preserved-parent';old.mkdir()
    for name in('POLICY.json','STATE.json','CURRENT.json','COMPLETE-RECEIPTS.json','SUPERVISOR.json'):
        shutil.copy2(ORIGINAL/'run'/name,old/name)
    (old/'world-tex').mkdir()
    for f in(Path(p['world'])/'files').rglob('*.tex'):
        if f.is_file()and not f.is_symlink():
            dest=old/'world-tex'/f.relative_to(Path(p['world'])/'files');dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    db.backup(sqlite3.connect(str(old/'knowledge.sqlite3')));db.close()
    pins=[{'path':str(ORIGINAL/'run'/name),'sha256':sha(ORIGINAL/'run'/name)}for name in('POLICY.json','STATE.json')]
    save(BASE/'BEFORE.json',{'at':time.time(),'knowledge_prefix':current['knowledge_event_prefix'],'gate_prefix':current['gate_event_prefix'],'parent_pins':pins,'original_policy':p,'original_state':state,'prior_task_ids':taskids,'prior_native_receipts':current['nodes'],'project_tasks':projects,'pending_queue':pending,'old_observer_before':before,'old_observer_after':identity(pid),'old_observer_lock_free_pause':paused,'worker_signals_sent':[],'old_phase_elapsed':True,'old_stop_retained':True,'new_phase_authority':'Latest explicit human supplement; not renewal or reset of original phase'})
    print(json.dumps({'captured':True,'knowledge_prefix':current['knowledge_event_prefix'],'prior_model_tasks':len(taskids),'prior_projects':len(projects),'pending':len(pending),'old_observer_lock_free_paused':paused}))

def acquire():
    for folder,ref,names in [('task',REF,['CODEX_TASK.md','README.md','STATUS.json']),('external-review',REVIEW_REF,['PUBLIC-MANIFEST.json'])]:
        root=BASE/'external'/folder;root.mkdir(parents=True,exist_ok=True)
        prefix='research/concept-transformations-2026-11-17/'if folder=='task'else'research/native-round2-external-review-2026-11-17/'
        for name in names:
            f=root/name
            if not f.exists():
                with urllib.request.urlopen('https://raw.githubusercontent.com/epsilon-lain/yohaku/'+ref+'/'+prefix+name,timeout=45)as r:raw=r.read(3000000)
                f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
        if folder=='external-review':
            manifest=json.loads((root/'PUBLIC-MANIFEST.json').read_bytes())
            for row in manifest['files']:
                f=root/row['path']
                if not f.exists():
                    with urllib.request.urlopen('https://raw.githubusercontent.com/epsilon-lain/yohaku/'+ref+'/'+prefix+row['path'],timeout=45)as r:raw=r.read(3000000)
                    f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(raw)
                if sha(f)!=row['sha256']or f.stat().st_size!=row['bytes']:raise RuntimeError('External review source differs: '+row['path'])
    task=BASE/'external/task/CODEX_TASK.md';raw=task.read_bytes()
    assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()=='c8085c72204526938a21ad5b62b44e5c6e05f515'
    original_activate(ORIGINAL/'run')
    from yohaku_ai_nodes import catalog
    c=catalog('openai');save(BASE/'ACTUAL-CATALOG.json',c)
    if not any(b.get('configured')and b.get('login',{}).get('state')=='signed_in'and any(m['id']=='gpt-6.1-sol'and all(e in m['executable_reasoning_efforts']for e in('high','max'))for m in b['models'])for b in c['backends']):raise RuntimeError('Sol High/Max unavailable')
    print(json.dumps({'fixed_task_git_blob_verified':True,'review_files_hash_verified':8,'catalog_sol_high_max_signed_in':True,'model_requests':0}))

def initialize():
    b=verify_parent()
    if(BASE/'POLICY.json').exists()or(BASE/'STATE.json').exists():raise RuntimeError('Supplement phase already exists; no reset')
    p=copy.deepcopy(b['original_policy']);v=copy.deepcopy(b['original_state'])
    p.update(experiment_id=PHASE,state_path=str(BASE/'STATE.json'),stop_file=str(BASE/'DRAIN'),catalog_path=str(BASE/'ACTUAL-CATALOG.json'),catalog_sha256=sha(BASE/'ACTUAL-CATALOG.json'),root_task='用户新增：概念转换、目标所需信息、逆向恢复与结构求解；应用继续真实实践',source_commit=REF,authorization='Explicit user supplement 2026-11-17 in this same Codex chat. Independent bounded delta phase; original phase expired and shared_stop is retained.',lineage={'parent_pins':b['parent_pins'],'original_turns_charged':len(v['turns']),'original_deadline':v['first_send_at']+p['limits']['seconds'],'original_stop':v['shared_stop'],'prior_ids_retained_in_parent':b['prior_task_ids'],'existing_members_and_leaders_reused':True,'old_budget_reset':False})
    # New user work receives its own explicit, limited delta authority. Old
    # phase has zero time remaining and is never described as renewed.
    p['limits']={'turns':12,'nodes':32,'concurrent':3,'seconds':10800,'task_seconds':900,'task_tools':96}
    p['common_instructions']+=' 本阶段为2026-11-17用户新增独立阶段，原阶段超时/停止/账本均保留。新增概念转换与目标信息研究，理论独立评价；原应用继续实践。先阅读新用户任务和原权威记忆，按需读数学精确版本。单任务900秒96工具，请自行拆为可保存的小任务/检查点；需要续行用research_continue，别在一个长收尾中悬空核验。原Stable08491已获随后外部完整复核，来源必须与原生失败分开；不可再要求它低于10。'
    save(BASE/'POLICY.json',p)
    state={'policy_sha256':sha(BASE/'POLICY.json'),'phase':'open','members':v['members'],'starts':{},'turns':{},'leaders':v['leaders'],'events':[{'seq':1,'at':time.time(),'kind':'independent_user_supplement_authority','parent_pins':b['parent_pins'],'parent_stop_unchanged':True,'prior_native_turns':len(v['turns']),'new_delta_limits':p['limits'],'no_node_creation':True}],'shared_stop':None,'first_send_at':None,'parent_liability_reference':p['lineage']}
    save(BASE/'STATE.json',state);save(BASE/'REGISTRATION.json',{'native_run_id':PHASE,'status':'prepared_not_dispatched','root_node_id':p['root_node_id'],'original_leaders':state['leaders'],'original_nodes_preserved':True,'new_nodes_created':0,'parent_policy_and_stop_unchanged':True,'new_user_instruction_phase':True,'policy_sha256':sha(BASE/'POLICY.json'),'limits':p['limits']})
    print(json.dumps({'initialized':True,'phase':PHASE,'new_nodes':0,'new_delta_limits':p['limits'],'old_stage_reset':False}))

def imports():
    verify_parent();p=activate()
    if(BASE/'IMPORT.json').exists():raise RuntimeError('Import registered; read original receipt')
    from yohaku_agent import Workspace
    from yohaku_native_research_runtime import service
    w=Workspace(p['world'],CANDIDATE/'bin/loom-linux-x86_64',CANDIDATE/'bin/yohaku_workspace');docs=[]
    for team in('theory','application'):
        for file in sorted((BASE/'external').rglob('*')):
            if not file.is_file():continue
            relative=file.relative_to(BASE/'external');name=relative.name;directory='files/'+team+'/round3-external/'+str(relative.parent)
            source=directory+'/'+name+'.tex'
            if(Path(p['world'])/source).exists():raise RuntimeError('External target already exists; preserve before retry')
            result=w.execute({'command':'create','directory':directory,'name':name,'body':file.read_text()})
            if result.get('sync_error'):raise RuntimeError(result)
            generated=Path(p['world'])/directory/name
            if sha(generated)!=sha(file):raise RuntimeError('Imported exact source body differs: '+str(file))
            docs.append({'team':team,'source':source,'source_revision':sha(Path(p['world'])/source),'generated_sha256':sha(generated),'external_relative':str(relative),'origin':'external_task_or_review_not_native_research'})
    k=service();eid='external/concept-transformations-20261117-resources'
    body=json.dumps({'task_commit':REF,'external_review_commit':REVIEW_REF,'files':docs,'external_review_result':'Stable08491 exactly10; author/native previous root task remains error/interrupted. External independent rebuild is not a native task. Read exact review for scope.','math_old_index':'Use math_search then exact math_read as needed; original seed_index unchanged.','old_official_inputs':'round2-external/resources.b64 plus RESOURCE-LOCK.json and restore_resources.py remain in both original projects.'},ensure_ascii=False,indent=2)
    entry={'id':eid,'revision':1,'title':'用户概念转换增补任务与随后外部Stable复核（非新原生研究）','summary':'新用户任务、精确固定外部来源；原Stable08491已被外部完整独立复核为10，原生超时记录不改。','body':body,'scope':'User supplemental direction and external evidence import','conditions':'External sources keep author/source attribution; no adoption or body reads prefilled','claim_kind':'external_seed','author_status':'External user task and external review; host imports only','independent_review_status':'hash_verified_external_import_not_new_review','source_group':'EXTERNAL','source_task':None,'author_node':'EXTERNAL_IMPORT','body_sha256':hashlib.sha256(body.encode()).hexdigest(),'at':time.time()}
    with k.tx()as db:
        if db.execute('SELECT 1 FROM entries WHERE id=?',(eid,)).fetchone():raise RuntimeError('Original shared entry exists')
        db.execute('INSERT INTO entries VALUES(?,?,?)',(eid,1,json.dumps(entry,ensure_ascii=False)))
        imported=k.event(db,{'actor_node_id':'HOST'},'external_seed',{'id':eid,'revision':1,'files':docs,'native_research_started':False,'actual_reads_or_adoptions_prefilled':False})
        user=k.event(db,{'actor_node_id':'HOST','source':'explicit_human_user'},'user_instruction_registered',{'request_id':REQUEST,'phase':PHASE,'task_commit':REF,'task_git_blob':'c8085c72204526938a21ad5b62b44e5c6e05f515','task_sha256':sha(BASE/'external/task/CODEX_TASK.md'),'task':(BASE/'external/task/CODEX_TASK.md').read_text(),'is_ai_continuation':False})
    save(BASE/'IMPORT.json',{'shared_math_id':eid,'revision':1,'external_event':imported,'user_instruction_event':user,'files':docs,'new_native_model_tasks':0})
    print(json.dumps({'imported_files':len(docs),'user_instruction_event':user,'shared_math_entry':eid+'@1','native_model_tasks':0}))

def dispatch():
    verify_parent();p=activate()
    from yohaku_ai_nodes import Control
    from yohaku_workflow_gate import gate
    from yohaku_native_research_runtime import service
    ctrl=Control(p['world']);root=next(n for n in ctrl.node_list()['nodes']if n['node_id']==p['root_node_id'])
    prior=next((t for t in root['tasks']if t['request_id']==REQUEST),None)
    if prior:
        status=ctrl.node_status(p['root_node_id'],REQUEST);save(BASE/'USER-ORIGINAL-STATUS.json',status);print(json.dumps({'task_id':prior['task_id'],'status':status['status'],'replayed':False}));return
    if not json.loads((BASE/'ENGINEERING-VALIDATION.json').read_bytes())['passed']:raise RuntimeError('Supplement fixture not validated')
    receipt=json.loads((BASE/'IMPORT.json').read_bytes());task=(BASE/'external/task/CODEX_TASK.md').read_text()
    task+='\n\n宿主现场交接（不是AI选题）：原阶段7个model任务及全部离线任务已按原ID确认终态/清理。root旧原turn已只读确认为interrupted；原STATE中的unknown/shared_stop均保留，旧六小时窗口已过，绝不改写成done。新阶段 '+PHASE+' 是当前用户新增任务的独立delta授权，不重置旧阶段或旧财务责任。新限额为12 native turns/3小时/同时3节点，单任务900秒96工具；先保存小检查点，自己选择研究任务边界和research_continue。原observer已在无应用锁边界暂停；宿主新observer只消费本阶段实际AI续题。\n'
    task+=json.dumps({'user_instruction_event':receipt['user_instruction_event'],'original_root_node':p['root_node_id'],'original_heads':gate().status()['leaders'],'original_group':p['group_id'],'original_chat':'ai-chat-7a7abc9f19d2de24731c6b27','resource_entry':receipt['shared_math_id']+'@1','resource_locations':['files/theory/round3-external/task/CODEX_TASK.md.tex','files/application/round3-external/task/CODEX_TASK.md.tex','files/{theory,application}/round3-external/external-review/README.md.tex'],'latest_external_stable_review':'0108519169ea786ed186d7c93aa13c33ffac625c; Stable08491最短10已有外部完整复核，不用再重构/挑战<10；准确保留原生失败和外部补核的不同来源','existing_research':'所有旧math版本/代码/官方资源/项目actions仍在，先读权威记忆和math索引；只新增round3-*源/action，别覆盖旧实验','work':'请自己通过原生工具派发原理论负责人补充概念/表示转换、目标信息、逆向恢复与结构求解；应用负责人继续真实实践并按需探索联系。两负责人max，其余至少high，仅Sol。请实际推进小研究题、证明/反例或真实计算；不止分发计划。你自己决定同伴/工具/复核/组织，没有强制新增节点或固定流水线。','finish':'安全边界保存权威记忆、中文数学稿和过程索引、原生task回执。完整外部补核文件可按需导入计算快照。宿主将整理公开成果至两仓库；比赛先保留可提交文件，平台本轮不上传。当前尚未宣称此增补已派发/已启动；以实际native task与turn回读为准。'},ensure_ascii=False,indent=2)
    prompt=BASE/'ROOT-REQUEST.txt'
    if prompt.exists():raise RuntimeError('Prepared immutable request exists without observed dispatch; inspect original registry before continuing')
    prompt.write_text(task)
    result=ctrl.node_dispatch(p['root_node_id'],REQUEST,task,profile={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}})
    save(BASE/'USER-DISPATCH.json',{'request_id':REQUEST,'kind':'user_directed','source_user_event':receipt['user_instruction_event'],'prompt_sha256':sha(prompt),'result':result,'at':time.time()})
    service().record({'actor_node_id':'HOST','source':'explicit_human_user'},'user_instruction_dispatched',{'request_id':REQUEST,'kind':'user_directed','result':result,'prompt_sha256':sha(prompt),'research_continue':False})
    print(json.dumps({'node_id':p['root_node_id'],'request_id':REQUEST,'task_id':result['task_id'],'status':result['status'],'profile':result.get('requested_profile'),'inference_confirmation_pending':True}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['capture','acquire','initialize','import','dispatch']);args=parser.parse_args();{'capture':capture,'acquire':acquire,'initialize':initialize,'import':imports,'dispatch':dispatch}[args.action]()

