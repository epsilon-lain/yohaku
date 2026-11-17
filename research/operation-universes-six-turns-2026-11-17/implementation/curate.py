"""Publishable whitelist: receipts, self-written results, frozen code/artifacts."""
import hashlib,json,sqlite3,time,zipfile
from pathlib import Path
from continuation import BASE,PHASE,LITERATURE,activate,verify_parent,save,sha

def put(root,name,value):
    f=root/name;f.parent.mkdir(parents=True,exist_ok=True)
    f.write_bytes(value if isinstance(value,bytes)else value.encode())

def main():
    from observer import observe
    x,allstatus,events,state=observe();p=activate();before=verify_parent()
    from yohaku_ai_nodes import Control
    from yohaku_project_tasks import Tasks
    y=BASE/'public-yohaku';m=BASE/'public-math';y.mkdir(exist_ok=True);m.mkdir(exist_ok=True)
    ids={t['task_id']for t in x['tasks']};ctrl=Control(p['world']);tasks=Tasks(p['world']);world=Path(p['world'])
    save(y/'evidence/STARTUP-AND-PROGRESS.json',x)
    for name in ('GOAL-RECEIPT.json','ENGINEERING-VALIDATION.json','TASK-TARGET-CONFIRMED.json'):
        put(y,'evidence/'+name,(BASE/name).read_bytes())
    save(y/'evidence/AUTHORITY-LINEAGE.json',dict(at=time.time(),new_phase=PHASE,
        limits=p['limits'],first_admission_at=x['first_admission_at'],exact_deadline=x['exact_deadline'],
        authorization=p['authorization'],prior_authority_charged=12,prior_authority_ceiling=12,
        parent_pins=before['parent_pins'],previous_stop=before['original_state']['shared_stop'],
        prior_model_tasks_clean=len(before['prior_task_ids']),prior_compute_tasks_clean=len(before['prior_project_tasks']),
        old_stop_cleared=False,old_budget_reset=False,old_memories_and_threads_preserved=True,
        old_observer_still_paused=before['old_observer_identity'],new_turns_include_all_ai_continuations=True))
    for name in ('continuation.py','observer.py','validate_authority.py','curate.py'):
        put(y,'implementation/'+name,(BASE/name).read_bytes())
    new=[e for e in events if e['seq']>before['knowledge_prefix']and e['actor'].get('task_id')in ids]
    published={(e['data']['id'],e['data']['revision'])for e in new if e['kind']=='math_published'}
    db=sqlite3.connect(p['knowledge_db'])
    math=[json.loads(r[0])for r in db.execute('SELECT value FROM entries ORDER BY id,revision')]
    db.close();math=[e for e in math if e.get('source_task')in ids and(e['id'],e['revision'])in published]
    for e in math:
        assert e['id'].startswith('M-')
        put(m,e['id']+'-v'+str(e['revision'])+'.zh.md',e['body'])
    save(m/'PROVENANCE.json',dict(at=time.time(),entries=[{k:e.get(k)for k in ('id','revision','title','summary','source_task','author_node','body_sha256','author_status','independent_review_status','conditions')}for e in math],not_an_IUT_corollary=True))
    document_refs=[]
    for team in('theory','application'):
        for f in sorted((world/'files'/team).glob('round5-*.tex')):
            d=ctrl.read(str(f.relative_to(world)));assert d['valid']
            rel=str(f.relative_to(world/'files')).removesuffix('.tex');put(y,'native-documents/'+rel,d['body'])
            document_refs.append(dict(source=str(f.relative_to(world)),source_revision=d['revision'],
                body_sha256=hashlib.sha256(d['body'].encode()).hexdigest(),public_path='native-documents/'+rel))
    save(y/'evidence/NATIVE-DOCUMENTS.json',document_refs)
    deps=[]
    for e in new:
        if e['kind']!='math_adopt':continue
        d=e['data'];source,sep,pinned=d['artifact'].partition('@');resolved={}
        try:
            if not source.endswith('.tex')and(world/(source+'.tex')).is_file():source+='.tex'
            body=ctrl.read(source)
            resolved=dict(canonical_artifact_source=source,artifact_revision=body['revision'],
                pinned_artifact_revision=pinned if sep else None,pinned_revision_matches=not sep or pinned==body['revision'],
                artifact_body_sha256=hashlib.sha256(body['body'].encode()).hexdigest(),literal_entry_id_in_artifact=d['id']in body['body'])
        except Exception as exc:resolved=dict(artifact_resolution_error=str(exc),dependency_not_certified=True)
        deps.append(dict(seq=e['seq'],actor=e['actor'],**d,**resolved,
            preceding_full_read_events=[r['event_seq']for r in x['actual_reads']if r['task_id']==e['actor']['task_id']and r['entry_id']==d['id']and r['revision']==d['revision']and r['full_body_returned']and r['event_seq']<e['seq']]))
    save(y/'evidence/ADOPTION-DEPENDENCIES.json',deps)
    meta=[];reviews=[]
    for e in new:
        row={k:e[k]for k in ('seq','at','kind','actor')}
        if e['kind']=='native_tool_completed':
            row.update(tool=e['data']['name'],ok=e['data']['result'].get('ok'),argument_keys=list(e['data']['arguments']))
            if e['data']['name']=='math_review':reviews.append(dict(seq=e['seq'],actor=e['actor'],arguments=e['data']['arguments'],result=e['data']['result']))
        meta.append(row)
    save(y/'evidence/EVENT-METADATA.json',meta);save(y/'evidence/NATIVE-REVIEW-RECEIPTS.json',reviews)
    compute=[]
    for item in x['computations']:
        s=item.get('status')or{}
        if not s.get('task_id'):continue
        tid=s['task_id'];r=tasks._owned(tid);directory=y/'experiments'/tid;directory.mkdir(parents=True,exist_ok=True)
        save(directory/'RECEIPT.json',s)
        for a in(r.get('receipt')or{}).get('artifacts',[]):
            file=Path(a['host_path']);assert sha(file)==a['sha256']
            assert '..'not in Path(a['path']).parts
            put(directory,'artifacts/'+a['path'],file.read_bytes())
        snapshot=r['snapshot'];files=snapshot['files'];maps=snapshot.get('mappings',[])
        private_names=('private-literature','round4-inputs','codex-provider','/memory/')
        safe=not any(any(b in z['path']for b in private_names)or z['path'].lower().endswith('.pdf')for z in files)
        safe=safe and not any(any(b in z.get('source','')for b in private_names)for z in maps)
        archive=None
        if safe:
            z=directory/'immutable-inputs.zip'
            if not z.exists():
                with zipfile.ZipFile(z,'x',zipfile.ZIP_DEFLATED)as out:
                    for row in files:
                        if row.get('role')=='map':continue
                        f=Path(snapshot['path'])/row['path'];assert sha(f)==row['sha256'];out.writestr(row['path'],f.read_bytes())
            with zipfile.ZipFile(z)as check:assert check.testzip()is None
            archive=dict(path='experiments/'+tid+'/immutable-inputs.zip',bytes=z.stat().st_size,sha256=sha(z))
        save(directory/'SNAPSHOT-MANIFEST.json',dict(snapshot_id=snapshot['id'],source_set=snapshot['source_set'],
            files=files,mappings=maps,archive=archive,private_literature_excluded=safe,map_sidecars_not_redistributed=True))
        compute.append(dict(task_id=tid,status=s['status'],source_set=snapshot['source_set'],archive=archive,
            receipt='experiments/'+tid+'/RECEIPT.json',artifacts=s.get('artifacts',[])))
    save(y/'evidence/COMPUTATIONS.json',compute)
    table=['|原角色|node|model task|状态|','|---|---|---|---|']
    for t in x['tasks']:table.append('|'+ '|'.join((t['role'],t['node_id'],t['task_id'],t['status']))+'|')
    rows=['|读取 node|精确版本|事件|完整正文|','|---|---|---|---|']
    for r in x['actual_reads']:rows.append('|'+ '|'.join((r['node_id'],r['entry_id']+'@'+str(r['revision']),str(r['event_seq']),str(r['full_body_returned'])))+'|')
    results='\n'.join('- `'+e['id']+'@'+str(e['revision'])+'`：'+e['title']+'。'+e['summary']for e in math)or'当前捕获尚无本轮新数学发布；启动不等于完成。'
    note=f'''# 原 Yohaku 团队：新增六回合授权实际接续

捕获：{x['observed_at_asia_shanghai']}，知识事件前缀{x['knowledge_prefix']}。本轮执行用户此前链接的运算宇宙包`7f41a0ef8008a7ced950e93be3730c74608e7abc`，用户再次明确确认继续该包；远端d320b81结构发现包未作为本轮新用户任务。

## 授权与真实启动

用户明确新增最多6个原生模型回合、首个准入起90分钟；全部负责人、协作者、审阅、模型自主续行均计入。首准入北京时间2026-11-17 16:34:54.181718，绝对截止18:04:54.181718。时间在第一次dispatch准入边界先记账，后续turn/start不能刷新。当前占{x['gate_status']['native_turns_reserved']}/6、余{x['gate_status']['native_turns_remaining']}，shared_stop={json.dumps(x['gate_status']['shared_stop'],ensure_ascii=False)}。

旧12/12与14:32:49截止、所有停止/失败/责任均保留原文件并固定SHA；没有清旧stop或重置账本。接续前沿原ID核19个旧模型和15个旧计算终态/清理，无pending。原观察器继续暂停；新增观察器只消费本阶段AI实际research_continue。原3节点、两方向和权威记忆保留，旧线程未删除；新任务的实际thread/turn以回读为准。

{chr(10).join(table)}

请求及原生thread配置均仅`gpt-6.1-sol / max`，每任务900秒/96工具上限；其他协作者最低Sol/high，无Astra/降级。实际provider内部身份/实扣费用仍unknown，不由配置反推。三者均已出现原生turn与真实用量/工具事件，非夹具自检。[完整启动/配置/用量/读取/计算回执](evidence/STARTUP-AND-PROGRESS.json)、[新授权及旧责任沿革](evidence/AUTHORITY-LINEAGE.json)、[准入夹具验证（零推理，非研究）](evidence/ENGINEERING-VALIDATION.json)。

## 两方向实际工作

原总负责人自行给两队派发小任务：理论选择复核上一轮幅度辅助信息界并研究条件复用，原负责人另复核理论的在线操作闭包；应用选择新的可还原条件转换/有界实验，避免重跑已完成的14球60窗。具体方法、复核、消息与续行由AI决定，非宿主固定流水线。当前任务状态只按上表，存在稿件/入队/推理/计算/完成分开。

{results}

独立复核范围以[实际math_review回执](evidence/NATIVE-REVIEW-RECEIPTS.json)和自写稿为准，不把作者自检或未运行枚举算作独立程序复算。比赛是否改善须等本轮具体路径与官方CLI；上轮15步换序/work130不算改善，旧15/work128继续保留，普通8/13和Stable08491=10只回归。[真实计算及产物清单](evidence/COMPUTATIONS.json)。本轮不上传平台或查榜。

## 文献、知识采用与过程

复用已核官方哈希的PANO/IUT1共11页及46权威.tex，不重复导入或倒填旧阅读。索引`external/operation-universes-20261117-resources@1`及原页版本不变；再次核revision/正文哈希。[输入复用回执](evidence/GOAL-RECEIPT.json)。以下仅本轮新任务实际math_read，均与工具返回全文哈希比对，旧事件2600..2841另留原包，不计成本轮新读取。

{chr(10).join(rows)}

完整PDF、逐页原文、公式图像、账户、原始聊天与权威记忆严格留本机；公式字形仍未完全认证。新命题独立证明，文献可辨散文只提供结构问题或警戒，不调用未经建立的IUT推论。[采用声明及对应产物revision/哈希和先前读取](evidence/ADOPTION-DEPENDENCIES.json)、[实际事件元数据（不含聊天/原文）](evidence/EVENT-METADATA.json)、[原生自写文件来源](evidence/NATIVE-DOCUMENTS.json)。

## 本机恢复

实际工程WSL archlinux `/root/projects/yohaku`。只读查询：
`python3 diagnostics/operation-universes-continuation-20261117-01/observer.py status`。
新阶段目录`diagnostics/operation-universes-continuation-20261117-01`；旧原文与旧回执在`diagnostics/operation-universes-literature-20261117`；原world及knowledge.sqlite3位置未变。未知请求只沿原ID查，不重放。公开数学整理到lain-s-note同名目录；此捕获后进展以新捕获或本机权威记录为准。
'''
    put(y,'README.zh.md',note)
    put(m,'README.zh.md','# 运算宇宙新增授权：原生数学成果\n\n捕获：'+x['observed_at_asia_shanghai']+'。旧成果不覆盖；本轮定义/证明/反例来源及范围如下。\n\n'+results+'\n\n原生模型请求与回读Sol/max。完整PDF/逐页全文/私有记忆不发布；无IUT推论或数学优先权声明。引用精确原生版本与作者/任务见[PROVENANCE](PROVENANCE.json)，实际独立复核见Yohaku过程包，不由发表推断已审阅。\n')
    for root in(y,m):save(root/'MANIFEST.json',dict(at=time.time(),full_original_literature_included=False,files=[dict(path=str(f.relative_to(root)),bytes=f.stat().st_size,sha256=sha(f))for f in sorted(root.rglob('*'))if f.is_file()and f.name!='MANIFEST.json']))
    print(json.dumps(dict(observed=x['observed_at_asia_shanghai'],tasks=[dict(id=t['task_id'],status=t['status'])for t in x['tasks']],math=len(math),documents=len(document_refs),reviews=len(reviews),computations=compute),ensure_ascii=False))
if __name__=='__main__':main()
