"""Seal a public receipt package after the finite native stage has closed."""
import hashlib,json,re,time,zipfile
from pathlib import Path
from continuation import BASE,activate,save,sha
PREFIX='research/native-mechanisms-execution-2026-11-17'
def main():
    p=activate();f=json.loads((BASE/'FINAL-LOCAL-STATUS.json').read_bytes());assert f['admission_closed']and f['all_models_done_committed_and_clean']
    from observer import observe
    x,_,_,state=observe();assert state['phase']=='closed'and not x['pending_queue']
    y=BASE/'public-yohaku';m=BASE/'public-math'
    prior=json.loads((y/'evidence/STARTUP-AND-PROGRESS.json').read_bytes());x['actual_source_page_reads']=prior.get('actual_source_page_reads',[]);save(y/'evidence/STARTUP-AND-PROGRESS.json',x)
    for name in('FINAL-LOCAL-STATUS.json','CLOSURE-AUDIT-ATTEMPT-1.json','GIT-PRESERVATION.json'):(y/'evidence'/name).write_bytes((BASE/name).read_bytes())
    for script in BASE.glob('*.py'):(y/'implementation'/script.name).write_bytes(script.read_bytes())
    lineage=json.loads((y/'evidence/AUTHORITY-LINEAGE.json').read_bytes());lineage.update(shared_stop=state['shared_stop'],phase='closed',unused_turns=8-len(state['starts']));save(y/'evidence/AUTHORITY-LINEAGE.json',lineage)
    programs=BASE.parent/'native-two-team-sol-20261116/run/home/.local/state/yohaku/project-tasks/work'
    search=json.loads((programs/'project-task-89caab5017f4956aa52cef38be06d56a/output/r6-results.json').read_bytes())
    review=json.loads((programs/'project-task-99f870b6bd681e7f0dccff953fb8bceb/output/r6-independent-results.json').read_bytes())
    submission=(programs/'project-task-99f870b6bd681e7f0dccff953fb8bceb/output/r6-independent-submission.txt').read_bytes();assert hashlib.sha256(submission).hexdigest()=='a5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2';(y/'submission.txt').write_bytes(submission)
    result=dict(goal_id=f['goal_id'],status=f['status'],model_turns=f['model_turns'],unused_turns=f['remaining_unused_turns'],all_models_done_and_clean=True,admission_closed=True,search=search['summary'],independent_acceptance=review,review_scope=f['independent_review_scope'],first_admission_at=f['first_admission_at'],absolute_deadline=f['absolute_deadline'],program_budget=f['program_budget'],publication_source_snapshot='Before the containing Git commit; final commit existence/readback is recorded separately by the host')
    save(y/'RESULTS.json',result)
    table=['|角色|实际node|实际model-task|终态|','|---|---|---|---|']+['|'+'|'.join((t['role'],t['node_id'],t['task_id'],t['status']))+'|'for t in x['tasks']]
    headline='''# Yohaku 原团队：本轮研究与独立验收已完成

本轮真实使用 **6/8 个原生模型回合**，全部请求和原生线程回读为 **gpt-6.1-sol / max**，全部 `done / completed / commit_confirmed / cleanup_complete`。首准入北京时间2026-11-17 **20:41:03.830741**，绝对截止 **22:11:03.830741**；本轮已关闭后续准入，未用2回合保留为未用责任，旧窗口的2回合没有复用。

理论交付为已知共同共轭见证下，限定 C/I 修复到指定 Stable 删除的最少原语数、残余框架、资源公式与反例；不是允许 M/S 的全图下界。[理论正文](native-library/M-538c85aecd32c8d0-v2.zh.md)及其7步小证书已由不同作者解析核对，并用固定官方代码和新写解释器逐态核为 **7步／work43／peak12**。

应用真实执行精确状态结构束搜索和反向半径4字典：**140329次搜索 apply，未找到<15路线**。逆字典347状态，前向完整层1..8；90秒边界后停止，9/10层未完成。固定宽度、rank<=3、词长<=96及实际丢弃范围都保留；它是有限负结果，不能称15最短。旧15步／work128／peak13保持。[可提交四行文件](submission.txt)已由不同作者另写解释器、固定官方CLI全路径核验；没有平台上传或榜单比较。

[AI自写最终中文说明](native-documents/theory/r6-final.zh.md) · [AI过程索引](native-documents/theory/r6-final-process-index.json) · [完整模型/读取/计算回执](evidence/STARTUP-AND-PROGRESS.json) · [研究结果](RESULTS.json) · [完整公开过程包ZIP](PROCESS-BUNDLE.zip)。自写报告是当时捕获，后续原生终态以宿主完整回读为准。

'''
    details='\n'.join(table)+'''

独立验收 `project-task-99f870b6bd681e7f0dccff953fb8bceb` 的210次验收调用中：新写解释器59、官方直接调用59、正式路径verify内部46、官方CLI46。含原实验91后，共 **301次验收**；与搜索一起由同一个持久硬账本拦截。保守已发租约140352／312，不退款，未闭合租约0；和真实调用数分列。全队硬帽2000000／50000。[逐producer预算](evidence/PROGRAM-BUDGET.json)及[原始计量账本ZIP](evidence/PROGRAM-LEDGER.zip)。

独立模型对实验摘要的review精确目标为 `M-faadd67bbdf57a62@1`。`@2`只将未完成深度的表述收窄，保留正文但**不自动继承@1复核**。路径验收另有 `M-110bcf615851324b@1`、完整逐状态/guard/CLI回执；搜索计数和逆字典未由另一作者独立重算。[复核原始范围](evidence/NATIVE-REVIEW-RECEIPTS.json)。

原应用负责人因预算参数包装错误保存了未执行记录；原ID查明未创建程序任务后，原总负责人在下一原生回合执行应用作者原封未改的冻结源。这个组织调整及一次新增验收同伴均来自团队实际选择。理论CI下界被应用队有理由拒作含M/S搜索的剪枝，但其精确小证书进入了独立验收程序。共享库的发布、全文读取、采用声明、源码依赖和复核分开留证；声明不代替运行。[采用与产物版本](evidence/ADOPTION-DEPENDENCIES.json)、[按需原文/代码读取](evidence/ACTUAL-SOURCE-READS.json)、[组织与消息元数据](evidence/WORKFLOW-EVENTS.json)。原始消息正文留在本机，公开为元数据与自写过程复述。

外部过程包c51ccae2的根MANIFEST及156文件、外部数学d2afe810的9个精确blob均已核验；数学目录根MANIFEST真实404已记录，未伪造。外部训练及旧宏收益保持原来源，不冒认本机发现；本轮没有同预算方法对照或加速声明。旧望月11页及全部原节点、记忆、停止、失败、预算账本保留，未倒填本轮论文阅读。旧12份POLICY/STATE哈希和原Git改动已核。[旧责任沿革](evidence/AUTHORITY-LINEAGE.json)、[工程失败及修复](evidence/ENGINEERING-HISTORY.json)、[Git保留核验](evidence/GIT-PRESERVATION.json)。

完整原生私有回执、消息、记忆和论文仍在本机；公开包只含自写稿、代码、路径、固定来源元数据和数学证据。输入ZIP提供相关源码/固定官方资源，完整原项目snapshot及映射继续留本机，不把子集ZIP声称为完整旧工程镜像。源捕获中的publication pending是写Git前时点；发布以包含本页的固定提交及宿主回读回执为准。

工程入口 WSL `archlinux:/root/projects/yohaku`。本轮目录 `diagnostics/native-mechanisms-20261117-01`，只读状态入口 `python3 diagnostics/native-mechanisms-20261117-01/observer.py status`。固定任务目标ID `native-mechanisms-next-20261117-v1`；重复任务应查原目标，不重新创建8回合。
'''
    (y/'README.zh.md').write_text(headline+details)
    (m/'README.zh.md').write_text('''# 原 Yohaku 团队：可迁移机制研究

本轮6/8原生回合均真实Sol/Max完成。理论得到已知共同框架见证下、只允许C/I直至指定Stable删除时的精确最少修复数和资源公式；残余框架、真实重编号及制造费用不能省略。[条件、证明、反例与小证书](M-538c85aecd32c8d0-v2.zh.md)。不同作者解析复核，并以固定官方代码和新写逐动作解释器把合成小证书核为7步/work43/peak12；该小例不是比赛原初态。

[应用真实有限负结果](M-faadd67bbdf57a62-v2.zh.md)：140329次搜索未找到sac-07445完整原语<15。逆B4=347，前向完整1..8层，90秒guard后9/10层未完成；有束宽/资源限制和状态丢弃，不能推出15最短或搜索加速。应用队明确拒把只适用于CI修复的理论下界用于含MS的beam。

[独立作者完整路径验收](M-110bcf615851324b-v1.zh.md)：四条正式路径的所有中间状态、资源、目标及固定官方CLI均通过，07445仍15/work128/peak13。没有平台上传或榜单成绩声明。实验摘要的独立review只针对@1；@2是更窄措辞，未自动继承复核。搜索/逆字典没有独立重算。

外部固定种子、经典自由群工具与本机增量分别标来源；不报数学优先权或IUT推论。所有旧版本保留，作者/任务/正文哈希见[PROVENANCE](PROVENANCE.json)。代码、过程、完整回执与可提交文件在epsilon-lain/yohaku同名目录；论文全文、原始聊天和私有记忆留本机。
''')
    for root in(y,m):
        files=[dict(path=str(q.relative_to(root)),bytes=q.stat().st_size,sha256=sha(q))for q in sorted(root.rglob('*'))if q.is_file()and q.name not in('MANIFEST.json','PROCESS-BUNDLE.zip')]
        save(root/'MANIFEST.json',dict(at=time.time(),bundle_self_excluded=True,full_private_text_included=False,files=files))
    bundle=y/'PROCESS-BUNDLE.zip'
    with zipfile.ZipFile(bundle,'w',zipfile.ZIP_DEFLATED)as z:
        for q in sorted(y.rglob('*')):
            if q.is_file()and q!=bundle:z.write(q,str(q.relative_to(y)))
    with zipfile.ZipFile(bundle)as z:assert z.testzip()is None
    output=[]
    for repo,branch,root in(('epsilon-lain/yohaku','codex/initial-release',y),('epsilon-lain/lain-s-note','main',m)):
        files=[]
        for q in sorted(root.rglob('*')):
            if not q.is_file():continue
            raw=q.read_bytes();rel=str(q.relative_to(root));assert not any(t in rel.lower()for t in('private-literature','codex-provider.json','memory.md','.pdf'))
            if q.suffix!='.zip':
                text=raw.decode();assert not re.search(r'\bsk-[A-Za-z0-9_-]{20,}',text)
            files.append(dict(path=PREFIX+'/'+rel,local=str(q),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),git_blob=hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest(),blob=q.suffix=='.zip'or len(raw)>80000))
        output.append(dict(repository=repo,branch=branch,prefix=PREFIX,files=files))
    save(BASE/'PUBLISH-PLAN.json',output);save(BASE/'PACKAGING.json',dict(at=time.time(),bundle_path=str(bundle),bundle_bytes=bundle.stat().st_size,bundle_sha256=sha(bundle),bundle_git_blob=hashlib.sha1(b'blob '+str(bundle.stat().st_size).encode()+b'\0'+bundle.read_bytes()).hexdigest(),files=[dict(repository=r['repository'],count=len(r['files']))for r in output],privacy_whitelist_passed=True))
    print(json.dumps(json.loads((BASE/'PACKAGING.json').read_bytes()),ensure_ascii=False))
if __name__=='__main__':main()
