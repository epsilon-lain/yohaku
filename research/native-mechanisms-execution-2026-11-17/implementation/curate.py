"""Publish only own results, source metadata, code, and verifiable receipts."""
import hashlib,json,sqlite3,time,zipfile
from pathlib import Path
from continuation import BASE,PHASE,activate,verify_parent,save,sha
def put(root,name,value):
    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(value if isinstance(value,bytes)else value.encode())
def private_message_metadata(value):
    if isinstance(value,list):return [private_message_metadata(x)for x in value]
    if not isinstance(value,dict):return value
    out={}
    for key,v in value.items():
        if key in('text','body','task','initial_task','host_operational_note')and isinstance(v,str):out[key+'_sha256']=hashlib.sha256(v.encode()).hexdigest();out[key+'_characters']=len(v)
        else:out[key]=private_message_metadata(v)
    return out
def main():
    from observer import observe
    x,current,events,state=observe();p=activate();before=verify_parent()
    from yohaku_ai_nodes import Control
    from yohaku_project_tasks import Tasks
    from mechanisms_host import rpc
    ctrl=Control(p['world']);world=Path(p['world']);taskapi=Tasks(world)
    y=BASE/'public-yohaku';m=BASE/'public-math';y.mkdir(exist_ok=True);m.mkdir(exist_ok=True)
    ids={t['task_id']for t in x['tasks']};new=[e for e in events if e['seq']>before['knowledge_prefix']and e['actor'].get('task_id')in ids]
    source_reads=[]
    for e in new:
        if e['kind']!='native_tool_completed'or e['data'].get('name')!='mechanism_source_read':continue
        reply=e['data'].get('result')or{};r=reply.get('result')or{};body=r.get('text','')
        if not reply.get('ok')or not body:continue
        digest=hashlib.sha256(body.encode()).hexdigest()
        source_reads.append(dict(event_seq=e['seq'],task_id=e['actor']['task_id'],node_id=e['actor']['actor_node_id'],entry_id=r['id'],revision=r['revision'],body_sha256=r['body_sha256'],offset=r['offset'],returned_body_characters=len(body),returned_body_sha256=digest,total_characters=r['total_characters'],next_offset=r.get('next_offset'),full_body_returned=r['offset']==0 and len(body)==r['total_characters']and digest==r['body_sha256'],source=r['source'],adoption_recorded=False))
    x['actual_source_page_reads']=[{k:v for k,v in r.items()if k!='source'}for r in source_reads]
    save(y/'evidence/STARTUP-AND-PROGRESS.json',x)
    save(y/'evidence/ACTUAL-SOURCE-READS.json',[{k:v for k,v in r.items()if k!='source'}for r in source_reads])
    for name in('FIRST-STARTUP-RECEIPT.json','THREE-NODE-STARTUP-RECEIPT.json','ENGINEERING-VALIDATION.json','ENGINEERING-HISTORY.json','ADAPTER-VALIDATION.json','RUNTIME-SEAL.json','RUNTIME-SEAL.v1.json','OBSERVER-REPLACEMENT.json','OFFICIAL-REF-CHECK.json','FINAL-LOCAL-STATUS.json','GIT-PRESERVATION.json'):
        if(BASE/name).exists():put(y,'evidence/'+name,(BASE/name).read_bytes())
    save(y/'evidence/AUTHORITY-LINEAGE.json',dict(at=time.time(),goal_id=PHASE,task_commit=p['source_commit'],authorization=p['authorization'],limits=p['limits'],first_admission_at=state['first_admission_at'],exact_deadline=state['first_send_at']+5400,native_admitted_attempts=len(state['starts']),native_turns=len(state['turns']),unused_turns=8-len(state['starts']),parent_pins=before['parent_pins'],old_model_tasks_terminal_clean=len(before['prior_task_ids']),old_program_tasks_terminal_clean=len(before['prior_computations']),old_unused_two_reused=False,shared_stop=state.get('shared_stop'),old_nodes_memories_failures_stops_preserved=True,private_memories_published=False))
    sources=json.loads((BASE/'SOURCE-CATALOG.json').read_bytes())
    save(y/'evidence/INPUT-SOURCES.json',dict(math_root_manifest_missing=True,math_fixed_git_blobs_verified=True,files=[{k:v for k,v in r.items()if k!='local'}for r in sources['files']]))
    for f in BASE.glob('*.py'):put(y,'implementation/'+f.name,f.read_bytes())
    for f in(BASE/'guard').glob('*'):
        if f.is_file():put(y,'implementation/guard/'+f.name,f.read_bytes())
    for name in('yohaku_native_research_runtime.py','yohaku_project_tasks.py','yohaku_native_research_gate.py','mechanisms_host.py'):put(y,'implementation/agent/'+name,(BASE/'candidate/agent'/name).read_bytes())
    db=sqlite3.connect(p['knowledge_db']);math=[json.loads(r[0])for r in db.execute('SELECT value FROM entries ORDER BY id,revision')];db.close();math=[e for e in math if e.get('source_task')in ids]
    for e in math:
        assert e['id'].startswith('M-');put(y,'native-library/'+e['id']+'-v'+str(e['revision'])+'.zh.md',e['body'])
        if e['id']!='M-8dcd6623caf5ee47':put(m,e['id']+'-v'+str(e['revision'])+'.zh.md',e['body'])
    save(m/'PROVENANCE.json',dict(entries=[{k:e.get(k)for k in('id','revision','title','summary','source_task','author_node','body_sha256','author_status','independent_review_status','conditions','evidence')}for e in math if e['id']!='M-8dcd6623caf5ee47'],old_versions_preserved=True,external_seed_is_not_native_discovery=True,interface_blocker_preserved_in_yohaku=True))
    documents=[]
    for team in('theory','application'):
        for f in sorted((world/'files'/team).glob('*.tex')):
            if not f.name.startswith(('r6-','round6-'))or 'memory'in f.name or f.name=='r6-start-checkpoint.json.tex':continue
            source=str(f.relative_to(world));d=ctrl.read(source);assert d['valid'];rel='native-documents/'+team+'/'+f.name.removesuffix('.tex');put(y,rel,d['body']);documents.append(dict(source=source,revision=d['revision'],body_sha256=hashlib.sha256(d['body'].encode()).hexdigest(),public_path=rel))
    save(y/'evidence/NATIVE-DOCUMENTS.json',documents)
    deps=[];reviews=[];flow=[];metadata=[]
    for e in new:
        row={k:e[k]for k in('seq','at','kind','actor')}
        if e['kind']=='native_tool_completed':
            d=e['data'];row.update(tool=d['name'],ok=d.get('result',{}).get('ok'),argument_keys=list(d.get('arguments',{})))
            if d['name']=='math_review':reviews.append(dict(seq=e['seq'],actor=e['actor'],arguments=d['arguments'],result=d['result']))
            if d['name']in('ai_node_create','ai_node_dispatch','ai_message_send','research_continue','research_finish','program_budget_allocate','program_budget_status','mechanism_source_read'):
                args=d['arguments'];result=d['result']
                if d['name']=='mechanism_source_read':result={'ok':result.get('ok'),'result':{k:v for k,v in(result.get('result')or{}).items()if k!='text'}}
                flow.append(private_message_metadata(dict(seq=e['seq'],at=e['at'],actor=e['actor'],tool=d['name'],arguments=args,result=result)))
        metadata.append(row)
        if e['kind']=='math_adopt':
            d=e['data'];source,sep,pin=d['artifact'].partition('@');extra={}
            try:
                if not source.endswith('.tex')and(world/(source+'.tex')).is_file():source+='.tex'
                body=ctrl.read(source);extra=dict(canonical_source=source,artifact_revision=body['revision'],pinned_revision=pin if sep else None,pinned_matches=not sep or pin==body['revision'],artifact_body_sha256=hashlib.sha256(body['body'].encode()).hexdigest(),literal_entry_id_in_artifact=d['id']in body['body'])
            except Exception as exc:extra=dict(unresolved_artifact=str(exc),dependency_not_certified=True)
            observed=next((z for z in reversed(events)if z['seq']<=e['seq']and z['kind']=='file_version_observed'and z['actor'].get('task_id')==e['actor']['task_id']and z['data']['source']==source),None)
            deps.append(dict(seq=e['seq'],actor=e['actor'],**d,**extra,artifact_observation_before_adopt=dict(event_seq=observed['seq'],revision=observed['data']['revision'])if observed else None,preceding_full_read_events=[r['event_seq']for r in x['actual_reads']+source_reads if r['task_id']==e['actor']['task_id']and r['entry_id']==d['id']and r['revision']==d['revision']and r['full_body_returned']and r['event_seq']<e['seq']]))
    save(y/'evidence/ADOPTION-DEPENDENCIES.json',deps);save(y/'evidence/NATIVE-REVIEW-RECEIPTS.json',reviews);save(y/'evidence/EVENT-METADATA.json',metadata);save(y/'evidence/WORKFLOW-EVENTS.json',flow)
    save(y/'evidence/CONTINUATION-RECEIPTS.json',[private_message_metadata(e)for e in events if e['seq']>before['knowledge_prefix']and e['kind']=='explicit_ai_continuation_consumed'])
    budget=rpc(p['program_budget']['socket'],dict(op='status'))
    bd=sqlite3.connect(p['program_budget']['database']);bd.row_factory=sqlite3.Row;ledger={table:[dict(r)for r in bd.execute('SELECT * FROM '+table)]for table in('meta','allocations','leases','events')};bd.close()
    budget['per_producer_reported']=[dict(allocation=a['id'],task_id=a['task'],reported={k:sum(r['reported']for r in ledger['leases']if r['allocation']==a['id']and r['kind']==k)for k in('search','verification')})for a in ledger['allocations']]
    save(y/'evidence/PROGRAM-BUDGET.json',budget)
    with zipfile.ZipFile(y/'evidence/PROGRAM-LEDGER.zip','w',zipfile.ZIP_DEFLATED)as z:z.writestr('ledger.json',json.dumps(ledger,ensure_ascii=False,indent=2)+'\n')
    calculations=[]
    for item in x['computations']:
        s=item.get('status')or{}
        if not s.get('task_id'):continue
        tid=s['task_id'];r=taskapi._owned(tid);directory=y/'experiments'/tid;directory.mkdir(parents=True,exist_ok=True);save(directory/'RECEIPT.json',s)
        for stream in('stdout','stderr'):
            log=taskapi.logs/(tid+'.'+stream)
            if log.is_file():put(directory,stream+'.txt',log.read_bytes())
        for a in(r.get('receipt')or{}).get('artifacts',[]):
            file=Path(a['host_path']);assert sha(file)==a['sha256'];assert '..'not in Path(a['path']).parts
            assert not a['path'].lower().endswith(('.pdf','.sqlite3'))and not any(t in a['path'].lower()for t in('private-literature','codex-provider','memory'))
            put(directory,'artifacts/'+a['path'],file.read_bytes())
        snap=r['snapshot'];selected=[]
        for f in snap['files']:
            path=f['path']
            if f.get('role')=='map':continue
            if path.startswith(('r6-','round6-'))or path.startswith('round2-external/')and Path(path).name in('restore_resources.py','resources.b64','RESOURCE-LOCK.json'):selected.append(f)
        zpath=directory/'REPRODUCIBLE-INPUTS.zip'
        with zipfile.ZipFile(zpath,'w',zipfile.ZIP_DEFLATED)as z:
            for f in selected:
                raw=(Path(snap['path'])/f['path']).read_bytes();assert hashlib.sha256(raw).hexdigest()==f['sha256'];z.writestr(f['path'],raw)
        with zipfile.ZipFile(zpath)as z:assert z.testzip()is None
        save(directory/'SNAPSHOT-MANIFEST.json',dict(snapshot_id=snap['id'],source_set=snap['source_set'],files=snap['files'],mappings=snap.get('mappings',[]),reproduced_files=selected,full_private_project_snapshot_published=False))
        calculations.append(dict(task_id=tid,status=s['status'],source_set=snap['source_set'],receipt='experiments/'+tid+'/RECEIPT.json',inputs_zip_sha256=sha(zpath),program_budget=r.get('program_budget'),artifacts=[{k:a.get(k)for k in('id','path','sha256','bytes')}for a in(r.get('receipt')or{}).get('artifacts',[])]))
    save(y/'evidence/COMPUTATIONS.json',calculations)
    results='\n'.join('- `'+e['id']+'@'+str(e['revision'])+'`：'+e['title']+'。'+e['summary']for e in math)or'尚无本轮原生数学发布。'
    table=['|角色|原node|model-task|状态|','|---|---|---|---|']+['|'+'|'.join((t['role'],t['node_id'],t['task_id'],t['status']))+'|'for t in x['tasks']]
    note='# 原 Yohaku 团队：可迁移机制与真实缩步研究\n\n固定目标 `'+PHASE+'`；执行任务版本 `3b729871d1ee83e4f3ab5ea048bfaa0fe67209ce`。捕获 '+x['observed_at_asia_shanghai']+'，知识事件前缀 '+str(x['knowledge_prefix'])+'。\n\n'+ '\n'.join(table)+'\n\n请求和原生线程回读仅 gpt-6.1-sol；负责人max，其他至少high。底层供应商内部模型身份及实扣费用unknown。准备、入队、原生turn确认、研究计算、完成分别看[完整状态](evidence/STARTUP-AND-PROGRESS.json)；已保存稿件不把error改为done。\n\n首准入20:41:03.831（北京时间2026-11-17），绝对截止22:11:03.831；共享8回合/5400秒，并发3，每任务900秒/96工具。当前准入尝试'+str(len(state['starts']))+'/8、原生turn '+str(len(state['turns']))+'；旧剩余2不复用，所有旧停止/失败/账本保持原文件SHA。首回合原生checkpoint从稍晚的reservation推算的截止比宿主绝对截止晚约0.956秒，权威时间以这里和[授权账本](evidence/AUTHORITY-LINEAGE.json)为准。\n\n'+results+'\n\n理论独立评价；限定操作类的下界不能称一般Stable最短性。应用主要目标sac-07445完整官方原语<15，原15/work128/peak13基线保留；具体搜索范围、成功或负结果看[native-documents/application](native-documents/application)和[全部真实程序回执](evidence/COMPUTATIONS.json)。所有最终路线需要固定官方CLI及独立解释器全程验收，训练/宏个数/work下降均不冒充严格缩步。未平台上传、未查榜。\n\n共享硬帽search apply2000000/verification apply50000；已发租约不退款，reported实际正常报告与issued保守责任分列：[程序预算](evidence/PROGRAM-BUDGET.json)、[逐进程原始账本](evidence/PROGRAM-LEDGER.zip)。独立解释器primitive也计verification。零推理硬帽夹具和模型自己做的无动作夹具均不算研究计算。预算参数包装曾前置拒绝task_submit、未预留程序ID；原错误保留，下一worker修复，模型回合照计；旧请求先查明不存在再接续，未覆盖原任务。\n\n外部流程输入固定c51ccae2、数学输入d2afe810。流程MANIFEST全156文件已核；数学仓该固定目录根MANIFEST真实404，以精确目录的9个Git blob/size/SHA校验补足。[全部来源元数据](evidence/INPUT-SOURCES.json)。本轮只按需读正文，旧望月原文11页留本机，本任务不要求重读，不倒填新阅读。外部成果、本机新证明、真正依赖分开：[读取/采用/产物对应](evidence/ADOPTION-DEPENDENCIES.json)、[独立原生复核](evidence/NATIVE-REVIEW-RECEIPTS.json)、[实际组织与消息事件](evidence/WORKFLOW-EVENTS.json)。没有配对实验不作协作或方法的因果收益声明。\n\n工程入口 WSL archlinux:/root/projects/yohaku；保留原world、节点、线程历史、记忆和全部旧版本。查询 `python3 diagnostics/native-mechanisms-20261117-01/observer.py status`。公开数学在 epsilon-lain/lain-s-note 同名研究目录，原始聊天/权威记忆/账户/论文全文仍留本机。\n'
    put(y,'README.zh.md',note)
    put(m,'README.zh.md','# 原生可迁移机制研究\n\n'+results+'\n\n来源/条件/作者与精确版本见[PROVENANCE](PROVENANCE.json)。外部种子保留云端来源，数学稿独立于比赛成绩评价。独立验收与全部计算证据在 Yohaku 同名目录。无数学优先权/IUT推论声明，不公开论文全文或私有记忆。\n')
    for root in(y,m):save(root/'MANIFEST.json',dict(at=time.time(),files=[dict(path=str(f.relative_to(root)),bytes=f.stat().st_size,sha256=sha(f))for f in sorted(root.rglob('*'))if f.is_file()and f.name!='MANIFEST.json']))
    print(json.dumps(dict(public_workflow_files=len(list(y.rglob('*'))),math_entries=len(math),reviews=len(reviews),programs=len(calculations),model_turns=len(state['turns']))))
if __name__=='__main__':main()
