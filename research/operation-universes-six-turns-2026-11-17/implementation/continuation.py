"""New explicit six-turn / 90-minute authority; original ledgers stay pinned."""
import argparse,copy,hashlib,json,os,sqlite3,sys,time
from pathlib import Path
BASE=Path(__file__).resolve().parent
PARENT=BASE.parent/'native-concept-transformations-20261117-03'
LITERATURE=BASE.parent/'operation-universes-literature-20261117'
ORIGINAL=BASE.parent/'native-two-team-sol-20261116'
sys.path.insert(0,str(ORIGINAL))
from prepare_native import activate as original_activate,save,sha,CANDIDATE
PHASE='operation-universes-native-sol-20261117-01'
REQUEST='user-operation-universes-six-turns-20261117-v1'
REF='7f41a0ef8008a7ced950e93be3730c74608e7abc'
USER='本轮授权新增最多6个原生模型回合、从首个准入起90分钟。请实际执行上述任务包，接续原团队，保留旧成果、失败和停止记录，返回真实启动回执。'
def activate():return original_activate(BASE)
def verify_parent():
    b=json.loads((BASE/'BEFORE.json').read_bytes())
    for r in b['parent_pins']:
        if sha(r['path'])!=r['sha256']:raise RuntimeError('Retained authority changed: '+r['path'])
    return b
def capture():
    if(BASE/'BEFORE.json').exists():raise RuntimeError('Existing baseline: inspect, never reset')
    p=original_activate(PARENT)
    from manage_native import snapshot,verify_candidate
    from yohaku_codex_tasks import read_record,alive,identity
    from yohaku_project_tasks import Tasks
    verify_candidate();current,events,entries,state=snapshot(PARENT)
    if not state['shared_stop']or current['gate_status']['remaining_seconds']!=0:raise RuntimeError('Expected expired stopped parent differs')
    ids=[]
    for n in current['nodes']:
        for t in n['tasks']:
            r=read_record(t['task_id'])
            if not(t.get('output_complete')and r.get('commit_confirmed')and(r.get('receipt')or{}).get('native_cleanup_complete'))or alive(r):raise RuntimeError('Original task unresolved: '+t['task_id'])
            ids.append(t['task_id'])
    projects=[];service=Tasks(p['world'])
    for f in(Path(p['home'])/'.local/state/yohaku/project-tasks/records').glob('*.json'):
        r=json.loads(f.read_bytes())
        if r.get('world')!=p['world']:continue
        s=service.status(task_id=r['task_id'])
        if s['status']not in('done','error','cancelled')or not(s.get('receipt')or{}).get('cleanup_confirmed'):raise RuntimeError('Original computation unresolved: '+r['task_id'])
        projects.append({'task_id':r['task_id'],'status':s['status']})
    db=sqlite3.connect(p['knowledge_db']);db.row_factory=sqlite3.Row
    pending=[dict(r)for r in db.execute("SELECT * FROM queue WHERE state='pending'")]
    if pending:raise RuntimeError('Original pending intent must be queried by original ID')
    db.backup(sqlite3.connect(str(BASE/'knowledge-before.private.sqlite3')));db.close()
    obs=json.loads((LITERATURE/'OBSERVER-IDLE-PAUSE.json').read_bytes())['identity'];live=identity(obs['pid'])
    if not live or live['start']!=obs['start']or live['state']!='T':raise RuntimeError('Old observer is not safely paused')
    pins=[]
    for stage in [ORIGINAL/'run',BASE.parent/'native-concept-transformations-20261117-01',BASE.parent/'native-concept-transformations-20261117-02',PARENT]:
        for name in('POLICY.json','STATE.json'):
            f=stage/name;pins.append({'path':str(f),'sha256':sha(f)})
    save(BASE/'BEFORE.json',{'at':time.time(),'knowledge_prefix':current['knowledge_event_prefix'],'parent_pins':pins,
        'original_policy':p,'original_state':state,'prior_task_ids':ids,'prior_native_receipts':current['nodes'],
        'prior_project_tasks':projects,'pending_queue':pending,'old_observer_identity':live,
        'old_stops_and_liabilities_retained':True,'new_authorization_exact_text':USER,
        'old_authority_turn_ceiling':12,'old_authority_turns_charged':12})
    print(json.dumps({'old_tasks_clean':len(ids),'old_computations_clean':len(projects),'pending':0,'new_models_started':0}))
def initialize():
    b=verify_parent()
    if(BASE/'POLICY.json').exists()or(BASE/'STATE.json').exists():raise RuntimeError('Grant exists: never reset')
    original_activate(PARENT)
    from yohaku_ai_nodes import catalog
    c=catalog('openai');save(BASE/'ACTUAL-CATALOG.json',c)
    if not any(r.get('configured')and r.get('login',{}).get('state')=='signed_in'and any(m['id']=='gpt-6.1-sol'and all(e in m['executable_reasoning_efforts']for e in('high','max'))for m in r['models'])for r in c['backends']):raise RuntimeError('Sol High/Max unavailable; no downgrade')
    p=copy.deepcopy(b['original_policy']);v=b['original_state']
    p.update(experiment_id=PHASE,state_path=str(BASE/'STATE.json'),stop_file=str(BASE/'DRAIN'),
        catalog_path=str(BASE/'ACTUAL-CATALOG.json'),catalog_sha256=sha(BASE/'ACTUAL-CATALOG.json'),
        root_task='新数值授权下接续运算宇宙、跨体系优势链与原应用实验',source_commit=REF,
        authorization={'kind':'explicit_human_user_new_numeric_authority','text':USER,'max_native_turns':6,'seconds_from_first_admission':5400},
        lineage={'parent_pins':b['parent_pins'],'previous_phase':b['original_policy']['experiment_id'],
            'previous_stop':v['shared_stop'],'previous_authority_charged':12,'previous_authority_ceiling':12,
            'previous_deadline_retained':v['first_send_at']+b['original_policy']['limits']['seconds'],
            'prior_task_ids':b['prior_task_ids'],'old_liabilities_reset':False,'new_numeric_grant':True},
        limits={'turns':6,'nodes':32,'concurrent':3,'seconds':5400,'task_seconds':900,'task_tools':96},
        common_instructions=b['original_policy']['common_instructions'].split(' 本阶段为2026-11-17用户新增独立阶段')[0]+
        ' 当前是用户明确新增最多6原生回合、首个准入起90分钟的独立授权；旧停止、失败和账本全保留，不重置、延时或重放。负责人每次Sol/max，其他至少Sol/high，无Astra或降级。每任务最多900秒96工具，显式profile不可继承旧1800/128。优先确保原两方向实际接续；自行选择问题、同伴、复核与方法，不要求增员或耗尽6回合。消息默认wake=[]；需要后续任务用research_continue，宿主只消费实际请求并夹紧剩余资源，不替AI选题。长任务及时存小产物/检查点并finish，不等待或长收尾超时。原文原版本已入共享库，先索引后精确正文；公开不复制整页/PDF/私有记忆。Stable08491最短10、普通8/13只回归。')
    save(BASE/'POLICY.json',p)
    state={'policy_sha256':sha(BASE/'POLICY.json'),'phase':'open','members':copy.deepcopy(v['members']),
        'starts':{},'turns':{},'leaders':copy.deepcopy(v['leaders']),
        'events':[{'seq':1,'at':time.time(),'kind':'explicit_new_user_numeric_authority','user_text':USER,
                   'limits':p['limits'],'parent_pins':b['parent_pins'],'old_stops_unchanged':True}],
        'shared_stop':None,'first_send_at':None,'first_admission_at':None,'parent_liability_reference':p['lineage']}
    save(BASE/'STATE.json',state)
    save(BASE/'REGISTRATION.json',{'at':time.time(),'phase':PHASE,'status':'prepared_not_dispatched',
        'new_grant':p['authorization'],'limits':p['limits'],'clock_started':False,
        'original_root_node':p['root_node_id'],'original_leaders':state['leaders'],'old_budget_reset':False,'old_stop_cleared':False})
    print(json.dumps({'registered':True,'limits':p['limits'],'clock_started':False,'model_requests':0}))
def import_goal():
    verify_parent();p=activate()
    if(BASE/'GOAL-RECEIPT.json').exists():raise RuntimeError('Goal exists: read original receipt')
    from yohaku_native_research_runtime import service
    from yohaku_ai_nodes import Control
    k=service();ctrl=Control(p['world']);imp=json.loads((LITERATURE/'IMPORT-RECEIPT.json').read_bytes())
    for doc in imp['native_documents']:
        d=ctrl.read(doc['source'])
        if not d['valid']or d['revision']!=doc['source_revision']or hashlib.sha256(d['body'].encode()).hexdigest()!=doc['body_sha256']:raise RuntimeError('Retained source changed: '+doc['source'])
    with k.tx()as db:
        for page in imp['page_entries']:
            r=db.execute('SELECT value FROM entries WHERE id=? AND revision=?',(page['id'],page['revision'])).fetchone()
            if not r or json.loads(r[0])['body_sha256']!=page['body_sha256']:raise RuntimeError('Exact private page missing')
        event=k.event(db,{'actor_node_id':'HOST','source':'explicit_human_user'},'user_instruction_registered',
            {'request_id':REQUEST,'phase':PHASE,'user_text':USER,'task_commit':REF,
             'task_sha256':sha(LITERATURE/'CODEX_TASK.md'),'task':(LITERATURE/'CODEX_TASK.md').read_text(),
             'new_max_turns':6,'new_seconds_from_first_admission':5400,'is_ai_continuation':False,
             'reused_literature_import_event':imp['import_event'],'actual_new_reads_prefilled':False})
    save(BASE/'GOAL-RECEIPT.json',{'at':time.time(),'user_event':event,'request_id':REQUEST,'task_commit':REF,
        'task_sha256':sha(LITERATURE/'CODEX_TASK.md'),'verified_retained_documents':len(imp['native_documents']),
        'retained_exact_page_versions':imp['page_entries'],'literature_index':'external/operation-universes-20261117-resources@1',
        'old_read_receipts_preserved':True,'actual_new_reads_prefilled':False,'actual_adoptions_prefilled':False,'model_requests':0})
    print(json.dumps({'user_event':event,'reused_pages':11,'verified_documents':46,'new_models':0}))
def dispatch():
    verify_parent();p=activate()
    from yohaku_ai_nodes import Control
    from yohaku_workflow_gate import gate
    from yohaku_native_research_runtime import service
    ctrl=Control(p['world']);g=gate();root=next(n for n in ctrl.node_list()['nodes']if n['node_id']==p['root_node_id'])
    prior=next((t for t in root['tasks']if t['request_id']==REQUEST),None)
    if prior:
        s=ctrl.node_status(p['root_node_id'],REQUEST);print(json.dumps({'original_task_id':prior['task_id'],'status':s['status'],'replayed':False}));return
    if not json.loads((BASE/'ENGINEERING-VALIDATION.json').read_bytes())['passed']:raise RuntimeError('Authority fixture not validated')
    if(BASE/'ROOT-REQUEST.txt').exists():raise RuntimeError('Prompt exists: inspect original ID before retry')
    goal=json.loads((BASE/'GOAL-RECEIPT.json').read_bytes());b=verify_parent()
    task=(LITERATURE/'CODEX_TASK.md').read_text()+'\n\n【最新用户数值授权及接续边界，以此覆盖旧额度描述】\n'+USER+'\n'
    task+='你仍是原总负责人'+p['root_node_id']+'；新用户event'+str(goal['user_event'])+'，新幂等键'+REQUEST+'。旧12/12及14:32:49截止/stop不动；本段是明确新增6回合/5400秒，首个准入开始不能刷新。上轮root model-task-d1bc98e338842bb8ab774ca582b3e06d仍error/600秒、原turn只读查interrupted。已沿原ID核'+str(len(b['prior_task_ids']))+'个旧model和'+str(len(b['prior_project_tasks']))+'个计算终态/清理，无pending。旧observer继续暂停；新observer只消费本授权内实际AI续行。\n'
    task+='请先给原理论/应用负责人实际接续小任务，然后你们自行选择问题、同伴、复核、工具、方法和后续回合，不预设流水线/必须增员。原heads='+json.dumps(g.status()['leaders'])+'，原group='+p['group_id']+'，原chat=ai-chat-7a7abc9f19d2de24731c6b27。总6回合/并发3，优先留原两head名额。所有负责人每次dispatch显式profile={provider:openai,model:gpt-6.1-sol,reasoning_effort:max,budget:{timeout_seconds:900,max_tool_calls:96}}；其他至少Sol/high，无Astra/降级，不继承旧1800/128。\n'
    task+='本包上轮已真实执行，尚未启动之类是原包历史文字，不要重做准备或倒填结果。原文11页和索引external/operation-universes-20261117-resources@1及各页external/mochizuki/PANO/p011@1等仍在，46权威.tex刚再核revision/正文哈希。先math_search索引/已有数学，按需math_read精确版本；旧阅读2600..2841保留，本轮阅读另留事件，必要重读说明范围。整页/PDF私有、公式字形未认证，不能依乱码用IUT定理。\n'
    task+='已有原生数学：M-e3e7a0b3682b081e@1（操作闭包q^r与两匹配）；M-2149d7062a0719a3@1（固定幅度0/1/q−1位）；M-1729534495821452@1（反演/共轭交换与窗口代码）；M-c772d35d33d375d7@1（14个radius3入口/60窗口/51301调用无缩步）。先按需读，别无目的重复；自主选择独立复核/新条件/反例/推进。新文稿/源码/action用round5-*，旧round2/3/4及失败保留。旧2→2换序15步合法但work128→130，不是收益。\n'
    task+='应用自主选择Stable07445或其他未证最短实例，锁基线/规则/预算/单位。官方main宿主本次核仍a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e；普通8/13和Stable08491=10只回归。task_submit只一次，未知沿原ID查；用官方CLI检查全部中间状态/资源/终点，留可提交文件，不上传/不查榜。按宏展开原始步数，有限负结果照存，无对照不报速度/token收益。\n'
    task+='及时完成小交付并research_finish，不等待两方向或长收尾挤到900秒。需要下一任务用research_continue明确目标/交付/验证，宿主只消费真实请求并夹紧900/96和剩余时间，不替AI选题。消息默认wake=[]避免隐式耗回合。AI自主任务与本用户目标分账；文献发布/读取/采用声明/实际依赖分开。公开只自写数学、必要短引文、URL/hash和证据，整页/账号/原始聊天/权威记忆不得进公开快照。宿主随后整理到两仓库。'
    (BASE/'ROOT-REQUEST.txt').write_text(task)
    with g.admission_guard()as v:
        if v['starts']or v['turns']or v.get('first_admission_at'):raise RuntimeError('Admission already exists: query IDs')
        now=time.time();v['first_admission_at']=now;v['first_send_at']=now
        g.event(v,'explicit_first_dispatch_admission_clock',at_authority=now,deadline=now+5400,source_user_event=goal['user_event'])
    result=ctrl.node_dispatch(p['root_node_id'],REQUEST,task,profile={'provider':'openai','model':'gpt-6.1-sol','reasoning_effort':'max','budget':{'timeout_seconds':900,'max_tool_calls':96}})
    save(BASE/'USER-DISPATCH.json',{'at':time.time(),'request_id':REQUEST,'source_user_event':goal['user_event'],
        'kind':'user_directed','prompt_sha256':sha(BASE/'ROOT-REQUEST.txt'),'result':result,
        'first_admission_at':now,'deadline':now+5400,'new_turn_ceiling':6,'old_budget_reset':False})
    service().record({'actor_node_id':'HOST','source':'explicit_human_user'},'user_instruction_dispatched',
        {'request_id':REQUEST,'source_user_event':goal['user_event'],'kind':'user_directed','result':result,'first_admission_at':now,'deadline':now+5400})
    print(json.dumps({'node':p['root_node_id'],'task_id':result['task_id'],'status':result['status'],'request':REQUEST,
        'first_admission_at':now,'deadline':now+5400,'native_turn_confirmation_pending':True}))
if __name__=='__main__':
    a=argparse.ArgumentParser();a.add_argument('action',choices=['capture','initialize','import-goal','dispatch']);args=a.parse_args()
    {'capture':capture,'initialize':initialize,'import-goal':import_goal,'dispatch':dispatch}[args.action]()
