"""Combine original-grant and inspected recovery receipts without hiding errors."""
import hashlib,json,sqlite3,time
from pathlib import Path
from continuation import BASE,activate,verify_parent,save,sha

def main():
    from curate import main as curate
    curate();p=activate();verify_parent();recovery=BASE.parent/'operation-universes-continuation-20261117-02'
    y=BASE/'public-yohaku';m=BASE/'public-math'
    def put(root,name,data):
        f=root/name;f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(data if isinstance(data,bytes)else data.encode())
    x1=json.loads((BASE/'STARTUP-AND-PROGRESS.json').read_bytes());x2=json.loads((recovery/'STARTUP-AND-PROGRESS.json').read_bytes())
    s1=json.loads((BASE/'STATE.json').read_bytes());s2=json.loads((recovery/'STATE.json').read_bytes())
    r=json.loads((recovery/'AI-CONTINUATION-DISPATCH.json').read_bytes());b=json.loads((recovery/'BEFORE.json').read_bytes())
    for pin in b['parent_pins']:assert sha(pin['path'])==pin['sha256']
    assert s1['first_send_at']==s2['first_send_at']==s1['first_admission_at']==s2['first_admission_at']
    used=len(s1['turns'])+len(s2['turns']);assert used<=6
    tasks=x1['tasks']+x2['tasks'];ids={t['task_id']for t in tasks};reads=x1['actual_reads']+x2['actual_reads']
    queries=json.loads((BASE/'FAILED-TURN-QUERIES.json').read_bytes())
    for t in tasks:
        q=next((v for v in queries['results']if v['task_id']==t['task_id']),None)
        if q:t['server_turn_status_verified_by_original_id']=q['native_status']
    grant=dict(original_ceiling=6,original_first_admission_at=s1['first_admission_at'],exact_deadline=s1['first_send_at']+5400,
        seconds_from_first_admission=5400,reserved_native_turns=used,remaining_native_turns=6-used,
        remaining_seconds=max(0,s1['first_send_at']+5400-time.time()),
        phase01_reserved=len(s1['turns']),recovery02_reserved=len(s2['turns']),
        phase02_capacity_is_remaining_not_additional=True,new_time_or_turns_added_by_recovery=False,
        phase01_stop_retained=s1['shared_stop'],current_phase02_stop=s2['shared_stop'])
    combined=dict(captured_at=time.time(),phase01_observed_at=x1['observed_at_asia_shanghai'],phase02_observed_at=x2['observed_at_asia_shanghai'],
        user_event=2974,task_commit='7f41a0ef8008a7ced950e93be3730c74608e7abc',grant=grant,tasks=tasks,actual_reads=reads,
        computations=x1['computations']+x2['computations'],adoption_events=x1['adoption_events']+x2['adoption_events'],
        tool_failures=x1['tool_failures']+x2['tool_failures'],pending_queue=x2['pending_queue'],
        parent_authorities_stops_failures_memories_preserved=True,original_full_text_remains_private=True)
    save(y/'evidence/STARTUP-AND-PROGRESS.json',combined)
    save(y/'evidence/PHASE01-RECEIPTS.json',x1);save(y/'evidence/PHASE02-RECEIPTS.json',x2)
    put(y,'evidence/FAILED-TURN-QUERIES.json',(BASE/'FAILED-TURN-QUERIES.json').read_bytes())
    save(y/'evidence/RECOVERY-CONSUMPTION.json',dict(at=r['at'],request_id=r['request_id'],source_user_event=r['source_user_event'],
        source_ai_event=r['source_ai_event'],source_queue_id=r['source_queue_id'],source_actor_task=r['source_actor_task'],
        task_id=r['result']['task_id'],kind=r['kind'],host_selected_mathematical_task=False,
        source_ai_task_sha256=hashlib.sha256(b['source_ai_continuation']['data']['task'].encode()).hexdigest(),
        exact_deadline=r['exact_deadline'],first_admission_at=r['first_admission_at'],new_time_or_turns_added=False,parent_pins=b['parent_pins']))
    for name in('continuation.py','observer.py'):
        put(y,'implementation/recovery02/'+name,(recovery/name).read_bytes())
    put(y,'implementation/aggregate_public.py',Path(__file__).read_bytes())
    from yohaku_ai_nodes import Control
    ctrl=Control(p['world']);docs=[]
    for team in('theory','application'):
        for f in sorted((Path(p['world'])/'files'/team).glob('round5-*.tex')):
            d=ctrl.read(str(f.relative_to(p['world'])));assert d['valid'];rel=str(f.relative_to(Path(p['world'])/'files')).removesuffix('.tex')
            put(y,'native-documents/'+rel,d['body']);docs.append(dict(source=str(f.relative_to(p['world'])),revision=d['revision'],body_sha256=hashlib.sha256(d['body'].encode()).hexdigest()))
    save(y/'evidence/NATIVE-DOCUMENTS.json',docs)
    db=sqlite3.connect(p['knowledge_db']);db.row_factory=sqlite3.Row
    all_events=[dict(z,actor=json.loads(z['actor']),data=json.loads(z['data']))for z in db.execute('SELECT * FROM events WHERE seq>? ORDER BY seq',(json.loads((BASE/'BEFORE.json').read_bytes())['knowledge_prefix'],))]
    math=[json.loads(z[0])for z in db.execute('SELECT value FROM entries ORDER BY id,revision')];db.close()
    math=[e for e in math if e.get('source_task')in ids]
    for e in math:
        assert e['id'].startswith('M-');put(m,e['id']+'-v'+str(e['revision'])+'.zh.md',e['body'])
    save(m/'PROVENANCE.json',dict(at=time.time(),entries=[{k:e.get(k)for k in('id','revision','title','summary','source_task','author_node','body_sha256','author_status','independent_review_status','conditions')}for e in math],old_versions_preserved=True,full_original_papers_reproduced=False))
    reviews=[];events=[];deps=[]
    for e in all_events:
        if e['actor'].get('task_id')not in ids:continue
        row={k:e[k]for k in('seq','at','kind','actor')}
        if e['kind']=='native_tool_completed':
            row.update(tool=e['data']['name'],ok=e['data']['result'].get('ok'),argument_keys=list(e['data']['arguments']))
            if e['data']['name']=='math_review':reviews.append(dict(seq=e['seq'],actor=e['actor'],arguments=e['data']['arguments'],result=e['data']['result']))
        events.append(row)
        if e['kind']=='math_adopt':
            d=e['data'];source,sep,pinned=d['artifact'].partition('@');extra={}
            try:
                if not source.endswith('.tex')and(Path(p['world'])/(source+'.tex')).is_file():source+='.tex'
                body=ctrl.read(source);extra=dict(canonical_source=source,artifact_revision=body['revision'],pinned_revision=pinned if sep else None,pinned_matches=not sep or pinned==body['revision'],artifact_body_sha256=hashlib.sha256(body['body'].encode()).hexdigest(),literal_entry_id_in_artifact=d['id']in body['body'])
            except Exception as exc:extra=dict(unresolved_artifact=str(exc),dependency_not_certified=True)
            deps.append(dict(seq=e['seq'],actor=e['actor'],**d,**extra,preceding_full_read_events=[v['event_seq']for v in reads if v['task_id']==e['actor']['task_id']and v['entry_id']==d['id']and v['revision']==d['revision']and v['full_body_returned']and v['event_seq']<e['seq']]))
    save(y/'evidence/NATIVE-REVIEW-RECEIPTS.json',reviews);save(y/'evidence/EVENT-METADATA.json',events);save(y/'evidence/ADOPTION-DEPENDENCIES.json',deps)
    table=['|原角色|node|model task|状态|','|---|---|---|---|']
    for t in tasks:table.append('|'+ '|'.join((t['role'],t['node_id'],t['task_id'],t['status']))+'|')
    pages=[v for v in reads if v['primary_literature']]
    page_text='\n'.join('- '+v['node_id']+'：`'+v['entry_id']+'@'+str(v['revision'])+'`，事件'+str(v['event_seq'])+'，返回全文哈希一致='+str(v['full_body_returned'])for v in pages)
    results='\n'.join('- `'+e['id']+'@'+str(e['revision'])+'`：'+e['title']+'。'+e['summary']for e in math)
    note=f'''# 原 Yohaku 团队：新增六回合授权实际执行回执

捕获：第一段{x1['observed_at_asia_shanghai']}；接续段{x2['observed_at_asia_shanghai']}。执行用户明确确认的原运算宇宙包`7f41a0ef8008a7ced950e93be3730c74608e7abc`，远端结构发现新包没有作为本轮任务。

## 真实启动、完成与失败

用户新目标事件2974；新授权最多6原生回合、首个准入起90分钟。首准入北京时间2026-11-17 16:34:54.181718，绝对截止18:04:54.181718。当前累计占{used}/6、剩{6-used}；接续段的3回合是原授权的剩余上界，不能与原6相加。没有新发回合或刷新时间。[完整启动/模型/用量/读取/计算回执](evidence/STARTUP-AND-PROGRESS.json)。

{chr(10).join(table)}

原总负责人实际派发原两方向；三者均真实Sol/max推理并保存产物。第一段root和理论负责人在900秒原生turn收尾超时，仍为error，不因已调用research_finish或已有稿件改为done；原ID thread/read均查interrupted，output_complete/commit_confirmed/native_cleanup_complete已确认。应用done，唯一新project计算done。前段shared_stop、旧12/12授权/14:32:49截止、所有失败及责任全部保留，原节点/记忆/线程历史不删除。

root在超时前已通过research_continue自主登记“核对两队证据”的唯一后续小任务（事件3605、queue4）。在全部终态/清理及原turn中断核实后，只消费该原请求：新task `{r['result']['task_id']}`；原请求不重放、不重做搜索，不由宿主选新题。当前状态见上表；该任务成功也不会覆盖第一段失败。[原ID中断查询](evidence/FAILED-TURN-QUERIES.json)、[同一剩余额度接续沿革](evidence/RECOVERY-CONSUMPTION.json)、[原授权和旧责任](evidence/AUTHORITY-LINEAGE.json)。

全部负责人请求和原生thread配置回读均`openai / gpt-6.1-sol / max`，每任务最多900秒/96工具，无Astra/降级；实际供应商内部身份及实扣费用仍unknown。回执包含每个thread/turn和本轮usage差量，准备、入队、turn确认、真实计算、完成分别记录，零推理夹具不算研究。

## 理论与应用实际产物

{results}

理论为条件明确的独立解析命题/反例，不要求即刻提升比赛成绩，不作数学优先权或IUT推论声明。根节点和理论负责人实际进行交叉解析复核，范围见[原生math_review回执](evidence/NATIVE-REVIEW-RECEIPTS.json)；代码/有限数据的源码核读不冒称独立程序复算。

应用唯一实际计算`project-task-c0f44bc9f068248f856aa641a7c3aac4`，冻结source_set `fa80ff558a1cbf299854a57601d3fb42ed0e83321606a2385de1f6e94c3512b1`。对Stable07445旧15/work128路线，只允许精确同端点、资源不增的相邻交换和精确二步环删除，定向闭包完整排空为2条路线；28个邻位、32次真实包装apply、无guard、无环、无缩步，仍15/peak13/work128。它是这个明确转换类的完整负结果，不能推全Stable15最短，也不是上轮半径3/60窗重跑。没有双臂/测试集，不报搜索或token加速。

最终四行提交固定官方`a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`真实CLI rc0/accepted，原始步数13/8/15/10，旧15/work128优先保留。[全部计算/源码/产物入口](evidence/COMPUTATIONS.json)，其中有完整原始结果、中间字状态、证书、CLI stdout/stderr、提交文件及无论文原文的冻结代码压缩包。未上传平台、未查排行榜。

## 文献实际读取与知识依赖

原11页、46个两队权威.tex及索引精确版本已再次核revision/正文哈希，不重复导入；旧2600..2841读取留原记录，不倒填成本轮。本轮新任务的原文全文工具读取：

{page_text}

每条均配对math_read实际成功返回及版本正文SHA。[读取/采用/产物依赖分账](evidence/ADOPTION-DEPENDENCIES.json)。有采用声明不自动等于证明调用；文献实际用途是结构保留与重建的建模问题，命题和桥梁独立证明。公式字形仍未逐式认证，相关精细公式不采用。PANO和IUT1全文、逐页提取、图像、账户、原始聊天和权威记忆全留本机，公开只有自写稿、URL/hash/页号/版本及必要短引文。

## 工作流与恢复

原3节点未增员；总负责人自主分工，两方向选题和交叉复核、消息、保存检查点及续行的实际事件见[事件元数据](evidence/EVENT-METADATA.json)。没有预设必须发生分化。曾出现task_result_index参数错误，沿原计算ID纠正查询，未重放计算；HOST给过一次不唤醒模型的资源边界提醒，不能据此断言AI已采用或导致计划变化。

WSL archlinux `/root/projects/yohaku`。当前只读入口：`python3 diagnostics/operation-universes-continuation-20261117-02/observer.py status`；第一段入口仍保留于01目录，旧原文/回执仍在operation-universes-literature-20261117，原world和knowledge.sqlite3位置未变。旧观察器均暂停，当前观察器只消费本段实际AI请求；剩余额度或时间用尽不再准入。公开数学在lain-s-note同名目录。此页是固定捕获，之后状态看新回执或本机入口。
'''
    put(y,'README.zh.md',note)
    put(m,'README.zh.md','# 原团队运算宇宙研究：新增六回合授权成果\n\n本轮真实推理与产物均保留来源。第一段总负责人和理论模型任务900秒收尾超时error，应用done；已保存证明不改作任务成功。原总负责人自选的证据核对续行状态另见Yohaku过程回执。未扩额或延时。\n\n'+results+'\n\n精确版本、作者/原node/task、正文哈希与条件见[PROVENANCE.json](PROVENANCE.json)。独立解析复核范围以Yohaku原生回执为准，不把自检称独立复算。标准方法的自含新实例，无文献首创、IUT推论、速度或比赛缩步声明。整页论文和私有记忆不公开。\n')
    for root in(y,m):save(root/'MANIFEST.json',dict(at=time.time(),full_original_literature_included=False,files=[dict(path=str(f.relative_to(root)),bytes=f.stat().st_size,sha256=sha(f))for f in sorted(root.rglob('*'))if f.is_file()and f.name!='MANIFEST.json']))
    save(BASE/'LATEST-AGGREGATE.json',combined)
    print(json.dumps(dict(grant=grant,tasks=[dict(id=t['task_id'],status=t['status'])for t in tasks],math=len(math),reviews=len(reviews),new_original_page_reads=len(pages)),ensure_ascii=False))
if __name__=='__main__':main()
