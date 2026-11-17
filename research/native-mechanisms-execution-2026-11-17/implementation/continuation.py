"""A fresh finite user grant on the retained original native team."""
import copy,hashlib,json,os,sqlite3,subprocess,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
ORIGINAL=BASE.parent/'native-two-team-sol-20261116'
PREVIOUS=BASE.parent/'operation-universes-continuation-20261117-02'
CANDIDATE=BASE/'candidate'
PHASE='native-mechanisms-next-20261117-v1'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n');p.chmod(0o600)
def activate(stage=BASE):
    policy=Path(stage)/'POLICY.json';p=json.loads(policy.read_bytes());dev=json.loads((CANDIDATE/'runtime/CODEX-DEVELOPMENT.json').read_bytes())
    for key in list(os.environ):
        if key.startswith(('YOHAKU_WORKFLOW_','YOHAKU_BATCH_','YOHAKU_ADAPTION_','YOHAKU_IMMUNE_','YOHAKU_AUTONOMOUS_','YOHAKU_REVIEW_')):os.environ.pop(key,None)
    os.environ.update(HOME=p['home'],YOHAKU_WORKSPACE=p['world'],YOHAKU_LOOM=str(CANDIDATE/'bin/loom-linux-x86_64'),YOHAKU_CODEX_LINUX=dev['entry'],YOHAKU_CODEX_AUTH_HOME=dev['auth_home'],YOHAKU_CODEX_PROVIDER_FILE=dev['provider_file'],YOHAKU_OPEN_CAPACITY_FILE=str(BASE.parent/'credit-autonomous-session-20261108-01/MACHINE-CAPACITY.json'),YOHAKU_WORKFLOW_POLICY=str(policy),YOHAKU_WORKFLOW_POLICY_SHA256=sha(policy),YOHAKU_NO_MODEL_REQUESTS='0',PYTHONDONTWRITEBYTECODE='1')
    if str(CANDIDATE/'agent')not in sys.path:sys.path.insert(0,str(CANDIDATE/'agent'))
    return p
def snapshot(stage=BASE):
    sys.path.append(str(ORIGINAL));import manage_native
    manage_native.activate=activate
    return manage_native.snapshot(stage)
def verify_parent():
    b=json.loads((BASE/'BEFORE.json').read_bytes())
    for r in b['parent_pins']:
        if sha(r['path'])!=r['sha256']:raise RuntimeError('Retained authority changed: '+r['path'])
    for path,h in json.loads((BASE/'RUNTIME-SEAL.json').read_bytes())['files'].items():
        if sha(CANDIDATE/path)!=h:raise RuntimeError('New runtime changed: '+path)
    return b
def prepare():
    if(BASE/'POLICY.json').exists():raise RuntimeError('Existing goal stage: query original IDs, never reset')
    p=activate(PREVIOUS)
    from yohaku_ai_nodes import Control,catalog
    from yohaku_codex_tasks import read_record,alive,state_root
    from yohaku_project_tasks import Tasks
    current,events,entries,oldstate=snapshot(PREVIOUS)
    for n in current['nodes']:
        for t in n['tasks']:
            r=read_record(t['task_id'])
            if not(t.get('output_complete')and r.get('commit_confirmed')and(r.get('receipt')or{}).get('native_cleanup_complete'))or alive(r):raise RuntimeError('Old model task not clean: '+t['task_id'])
            if any(PHASE in str(t.get(k,''))for k in('node_request_id','task_id')):raise RuntimeError('Goal already has a native request')
    computations=[];project=Tasks(p['world'])
    for f in(Path(p['home'])/'.local/state/yohaku/project-tasks/records').glob('*.json'):
        r=json.loads(f.read_bytes())
        if r.get('world')!=p['world']:continue
        out=project.status(task_id=r['task_id']);computations.append(out)
        if out.get('status')not in('done','error','cancelled')or not(out.get('receipt')or{}).get('cleanup_confirmed'):raise RuntimeError('Old computation not clean: '+r['task_id']+' '+str(out.get('status')))
    db=sqlite3.connect(p['knowledge_db']);db.row_factory=sqlite3.Row
    pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'")]
    if pending:raise RuntimeError('Old pending AI request requires original-ID inspection')
    if db.execute('SELECT 1 FROM events WHERE data LIKE ? LIMIT 1',('%'+PHASE+'%',)).fetchone():raise RuntimeError('Fixed goal already recorded in knowledge history')
    db.backup(sqlite3.connect(str(BASE/'knowledge-before.private.sqlite3')));db.close()
    dirs=[ORIGINAL/'run']+[BASE.parent/('native-concept-transformations-20261117-'+x)for x in('01','02','03')]+[BASE.parent/('operation-universes-continuation-20261117-'+x)for x in('01','02')]
    pins=[dict(path=str(d/n),sha256=sha(d/n))for d in dirs for n in('POLICY.json','STATE.json')]
    save(BASE/'BEFORE.json',dict(at=time.time(),knowledge_prefix=current['knowledge_event_prefix'],parent_pins=pins,prior_task_ids=[t['task_id']for n in current['nodes']for t in n['tasks']],prior_nodes=current['nodes'],prior_computations=computations,old_stops_preserved=True,old_unused_two_reused=False))
    c=catalog('openai');save(BASE/'ACTUAL-CATALOG.json',c)
    acquired=json.loads((BASE/'ACQUISITION.json').read_bytes())['files'];rows=[]
    for row in acquired:
        local=row['local']
        if not local.startswith('external/'):continue
        _,origin,path=local.split('/',2);r=dict(row,origin=origin,path=path,local=str(BASE/local));assert sha(r['local'])==r['sha256'];rows.append(r)
    assert next(r for r in rows if r['origin']=='workflow'and r['path']=='MANIFEST.json')['git_blob']=='7b13617c3cdc2d8e574435965db8c595a4b950f4'
    save(BASE/'SOURCE-CATALOG.json',dict(files=rows,math_root_manifest_missing=True,math_fixed_directory_listing_fallback=True))
    guardhash={f.name:sha(f)for f in(CANDIDATE/'guard').iterdir()if f.is_file()}
    p.update(experiment_id=PHASE,goal_id=PHASE,state_path=str(BASE/'STATE.json'),stop_file=str(BASE/'DRAIN'),root_task='原团队可迁移机制与sac-07445严格缩步',source_commit='3b729871d1ee83e4f3ab5ea048bfaa0fe67209ce',catalog_path=str(BASE/'ACTUAL-CATALOG.json'),catalog_sha256=sha(BASE/'ACTUAL-CATALOG.json'),mechanism_catalog=str(BASE/'SOURCE-CATALOG.json'),
        limits=dict(turns=8,nodes=32,concurrent=3,seconds=5400,task_seconds=900,task_tools=96),
        authorization=dict(kind='explicit_new_user_grant',goal_id=PHASE,turns=8,seconds=5400,all_teams_shared=True,old_remainder_reused=False,source_user_message='本轮新授权最多8个原生模型回合、首次准入起90分钟，所有团队共享，旧剩余额度不复用。'),
        lineage=dict(parent_pins=pins,old_stops_preserved=True,old_unused_two_reused=False),
        program_budget=dict(socket=str(BASE/'apply.sock'),database=str(BASE/'apply.sqlite3'),guard_root=str(CANDIDATE/'guard'),guard_hashes=guardhash,search_cap=2000000,verification_cap=50000))
    p['common_instructions']='''你是 Yohaku 持久原生研究节点，原身份、历史、记忆、失败和停止全部保留。当前唯一新授权是 native-mechanisms-next-20261117-v1：全队合计最多8个原生模型回合，首次真实准入起5400秒，并发3；旧剩余2不复用。总负责人和理论/应用负责人必须gpt-6.1-sol/max，其他同伴至少Sol/high，禁止其它模型与降级。每任务<=900秒96工具且不越总截止。首个总负责人只读短索引、分工、保存检查点，争取300秒内结束，不等待两队研究；请给独立复核和最终收尾预留回合。你们自主选择问题、方法、帮手和分工，允许更多小队但共享8回合。用research_resources核本任务剩余时间，提前保存小产物，research_finish后立即简短最终答复。后续仅research_continue显式请求，宿主不另选题、不重置阶段。消息默认wake=[]，未知结果查原ID不重放。
共享数学库先math_search短索引，再math_read精确版本；发布/读取/采用/依赖/独立复核分别留证。外部云端成果不得冒认本机新发现。mechanism_sources_index/read按需读固定哈希正文/代码，可导入唯一.tex；数学body原文、私有记忆不公开。旧望月11页仅新依赖需要才读，不倒填阅读。
所有程序生产者必须先program_budget_allocate，然后task_submit传budget_allocation_id。本阶段全队硬帽search apply2000000/verification apply50000，包含失败/重试/子进程/verify内部；分配一次只能绑一个不可变producer/source_set，不回收失败已发租约。实际reported与保守issued分别记录。不要一次把全部帽分给一个producer，给独立验收预留。纯数学0/0可执行。程序限Python；官方core/stable_core.apply_move由可信运行时自动钩计，Python子进程也计，不允许非Python子进程绕过。固定官方源a0fd6e6f；自写独立解释器每个原始动作必须用from meter import independent_step装饰器计verification，或显式meter.verification上下文内调用固定官方apply。禁止关钩/复制改名官方core逃计。所有程序开始前冻结源/随机种子/候选/停止规则；最多任务900秒且夹紧阶段截止。
主要应用目标sac-07445完整官方原语<15，旧15步work128/peak13保持。方法必须区别于旧资源单调两路闭包/半径3/原路径固定DAG。精确有序约简tuple/rank/生成元编号，宏完全展开；任何改名/整体共轭/稳定化恢复都不免费。限制100000动作、词长10000、work5000000、rank8。最终固定官方CLI+独立解释器全路径验收，无改进保存有限负结果，不称15最短。不得平台上传或查榜。
理论自主选可迁移条件机制/规则族/指数和必要障碍等小一般问题，交精确定义、证明、反例和小证书；经典工具写来源，不强求立即改善比赛。跨队采用要有真实版本读取和后续代码/证明依赖，未采用也记录原因。保留旧v1排除动作，不重复训练清理冒称新发现。此次任务正文与短入口在external/mechanisms-20261117/index@1，先读该条。'''
    save(BASE/'POLICY.json',p)
    save(BASE/'STATE.json',dict(policy_sha256=sha(BASE/'POLICY.json'),phase='open',members=copy.deepcopy(oldstate['members']),leaders=copy.deepcopy(oldstate['leaders']),starts={},turns={},events=[dict(seq=1,at=time.time(),kind='explicit_new_user_authorization',goal_id=PHASE,turn_cap=8,seconds=5400,old_unused_two_reused=False)],shared_stop=None,first_send_at=None,first_admission_at=None,parent_liability_reference=p['lineage']))
    activate()
    from yohaku_native_research_runtime import service
    from yohaku_workflow_gate import gate
    k=service();ctrl=Control(p['world'])
    wanted=['SUMMARY.json','MECHANISMS.zh.md','symbolic_rules/RULES.json','SELECTED-CERTIFICATES.json','CLI-ACCEPTANCE.json','OFFICIAL-SOURCE-LOCK.json','independent_review/SUMMARY.json']
    selected=[r for r in rows if(r['origin']=='workflow'and r['path']in wanted)or(r['origin']=='math'and r['path']in('MECHANISMS.zh.md','symbolic-rules.zh.md','goal-suffix.zh.md','conjugation-frames.zh.md','fragment-selection.zh.md','boundary-encoding.zh.md'))]
    imports=[]
    def entry(eid,title,body,source,auth):
        e=dict(id=eid,revision=1,title=title,summary='固定外部来源；实际读取及采用另记',body=body,body_sha256=hashlib.sha256(body.encode()).hexdigest(),scope='external mechanism source',conditions='保留来源与适用范围',claim_kind='external_source',author_status='外部云端作者，不是本机新发现',independent_review_status='source bytes verified, not a native review',source_group='EXTERNAL',source_task=None,author_node='EXTERNAL_SOURCE',at=time.time(),source=source,authoritative_files=auth)
        with k.tx()as d:
            assert not d.execute('SELECT 1 FROM entries WHERE id=?',(eid,)).fetchone();d.execute('INSERT INTO entries VALUES(?,?,?)',(eid,1,json.dumps(e,ensure_ascii=False)))
            k.event(d,{'actor_node_id':'HOST'},'external_mechanism_imported',dict(id=eid,revision=1,body_sha256=e['body_sha256'],source=source,authoritative_files=auth))
        imports.append({key:e[key]for key in('id','revision','title','body_sha256','authoritative_files')})
    for r in selected:
        body=Path(r['local']).read_text();auth=[]
        for scope in p['project_scopes']:
            source=scope['root']+'/r6-inputs/'+r['origin']+'/'+r['path']+'.tex'
            back=ctrl.write(source,body,node=dict(id='r6-'+hashlib.sha256(source.encode()).hexdigest()[:24],name=r['path'],description='Fixed external source',entry=False));assert back['valid']and back['body']==body;auth.append(dict(source=source,revision=back['revision']))
        entry('external/mechanisms-20261117/source/'+r['origin']+'/'+r['path'],r['origin']+'/'+r['path'],body,r,auth)
    index='本轮任务与固定输入短索引。先按需math_read以下精确条目；代码用mechanism_sources_index/read导入项目。\n'+json.dumps(imports,ensure_ascii=False,indent=2)+'\n重要：数学仓固定目录没有根MANIFEST(真实404)，已用固定提交目录的9个Git blob/size/SHA核验；流程根MANIFEST 7b13617c...已核。外部规则11条，frames v2与符号010不双计；29例DP=greedy负结果不能保证未见状态；训练450→372为新旧后验选优。\n本轮CODEX任务全文：\n'+(BASE/'task/CODEX_TASK.md').read_text()
    entry('external/mechanisms-20261117/index','本轮机制研究短索引与用户任务',index,dict(task_commit=p['source_commit'],source_catalog_sha256=sha(BASE/'SOURCE-CATALOG.json')),[])
    save(BASE/'IMPORTS.json',imports)
    with k.tx()as d:k.event(d,{'actor_node_id':'USER'},'user_goal_registered',dict(goal_id=PHASE,authorization=p['authorization'],task_sha256=sha(BASE/'task/CODEX_TASK.md'),host_preparation_is_research=False))
    cfg=dict(p['program_budget'],goal_id=PHASE,state_path=p['state_path'],policy_sha256=sha(BASE/'POLICY.json'),model_records=str(state_root()),project_records=str(Path(p['home'])/'.local/state/yohaku/project-tasks/records'))
    save(BASE/'BUDGET-SERVER.json',cfg)
    for effort in('high','max'):gate().cached_profile(dict(provider='openai',model='gpt-6.1-sol',reasoning_effort=effort,budget=dict(timeout_seconds=900,max_tool_calls=96)))
    verify_parent();print(json.dumps(dict(prepared=True,imports=len(imports),old_model_tasks=len(current['nodes'][0]['tasks'])+sum(len(n['tasks'])for n in current['nodes'][1:]),old_computations=len(computations),actual_new_models=0,clock_started=False)))
def start_budget():
    p=activate();verify_parent()
    from yohaku_codex_tasks import identity
    from mechanisms_host import rpc
    if(BASE/'BUDGET-SERVER-ID.json').exists():
        old=json.loads((BASE/'BUDGET-SERVER-ID.json').read_bytes());live=identity(old['pid'])
        if live and live['start']==old['start']:
            print(json.dumps(dict(existing_server=True,status=rpc(p['program_budget']['socket'],dict(op='status')))));return
        if Path(p['program_budget']['socket']).exists():Path(p['program_budget']['socket']).unlink()
    with(BASE/'budget-server.log').open('ab')as log:child=subprocess.Popen([sys.executable,'-B',str(BASE/'guard/budget_server.py'),str(BASE/'BUDGET-SERVER.json')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,start_new_session=True)
    for _ in range(100):
        if Path(p['program_budget']['socket']).exists():break
        if child.poll()is not None:raise RuntimeError('Budget server failed: inspect log')
        time.sleep(.05)
    save(BASE/'BUDGET-SERVER-ID.json',identity(child.pid));print(json.dumps(dict(server_pid=child.pid,status=rpc(p['program_budget']['socket'],dict(op='status')))))
def dispatch():
    verify_parent();p=activate()
    assert json.loads((BASE/'ENGINEERING-VALIDATION.json').read_bytes())['passed']
    from yohaku_ai_nodes import Control
    from yohaku_workflow_gate import gate
    ctrl=Control(p['world']);root=next(n for n in ctrl.node_list()['nodes']if n['node_id']==p['root_node_id'])
    request=PHASE+'-initial'
    prior=next((t for t in root['tasks']if t['request_id']==request),None)
    if prior:print(json.dumps(ctrl.node_status(p['root_node_id'],request)));return
    prompt='''这是用户明确新增的本轮目标，不是AI自提任务。接续你与原理论负责人ai-node-b912b62d9e95d94ddb26bfd6、应用负责人ai-node-0299a356d74db83b9ab4ebc7，保留原记忆/节点/失败/停止。上轮已终止且全部旧model/program都已按原ID查清terminal/clean，旧2回合不复用。本轮独立全队共享8回合/首准入90分钟；负责人Sol/max、协作者至少Sol/high，并发3，每任务900秒96工具。本首回合争取300秒内主动结束：先math_read external/mechanisms-20261117/index@1及你所需短SUMMARY/MECHANISMS；自行短分工，实际以显式profile派发原两负责人（900秒96工具,max），保存计划/记忆，预留独立复核及收尾回合。不要等待两队完成。后续需求由research_continue显式登记，由同阶段observer消费；未请求不由宿主替你选题。
请把全文任务交给两方向按需读。理论自主选可迁移机制/规则族/必要障碍的一般小命题及反例小证书；应用先冻结区别于旧两路交换闭包/半径3/原路径固定DAG的新方法，尝试sac-07445官方完整原语<15，15/work128/peak13未改。外部成果保留外部作者；索引/正文/采用/依赖/真实计算/独立复核分开。所有程序先program_budget_allocate再task_submit预算ID；单producer一次绑定不可变源，全队search2000000/verification50000硬帽，失败和子进程也入账。建议额度按实际需要小份分配并给独立验收留量，不把全帽一次占完。固定官方与自写独立逐动作计量方式见common_instructions。最终独立验收，不上传比赛、不查榜。
你们自主决定选题、组织、同伴、方法、修订；允许小队但没有额外回合。报告采用/拒用与消息触发变化。不要把准备/入队/夹具说成研究启动。当前程序源已可按需mechanism_source_read导入r6-inputs唯一.tex；旧round2-external固定官方资源也保留。research_resources新增本task剩余秒数，及时存小稿，research_finish后立即最终回复结束原生回合。'''
    (BASE/'ROOT-REQUEST.txt').write_text(prompt)
    g=gate()
    with g.admission_guard()as v:
        if v.get('first_send_at'):raise RuntimeError('Original first admission already exists; inspect fixed goal')
        v['first_send_at']=v['first_admission_at']=time.time();g.event(v,'first_real_admission_clock_started',goal_id=PHASE,deadline=v['first_send_at']+5400)
    result=ctrl.node_dispatch(p['root_node_id'],request,prompt,profile=dict(provider='openai',model='gpt-6.1-sol',reasoning_effort='max',budget=dict(timeout_seconds=900,max_tool_calls=96)))
    save(BASE/'INITIAL-DISPATCH.json',dict(at=time.time(),request_id=request,result=result,actual_start_requires_thread_turn_readback=True));print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':{'prepare':prepare,'budget':start_budget,'dispatch':dispatch}[sys.argv[1]]()
