# Yohaku 原团队：本轮研究与独立验收已完成

本轮真实使用 **6/8 个原生模型回合**，全部请求和原生线程回读为 **gpt-6.1-sol / max**，全部 `done / completed / commit_confirmed / cleanup_complete`。首准入北京时间2026-11-17 **20:41:03.830741**，绝对截止 **22:11:03.830741**；本轮已关闭后续准入，未用2回合保留为未用责任，旧窗口的2回合没有复用。

理论交付为已知共同共轭见证下，限定 C/I 修复到指定 Stable 删除的最少原语数、残余框架、资源公式与反例；不是允许 M/S 的全图下界。[理论正文](native-library/M-538c85aecd32c8d0-v2.zh.md)及其7步小证书已由不同作者解析核对，并用固定官方代码和新写解释器逐态核为 **7步／work43／peak12**。

应用真实执行精确状态结构束搜索和反向半径4字典：**140329次搜索 apply，未找到<15路线**。逆字典347状态，前向完整层1..8；90秒边界后停止，9/10层未完成。固定宽度、rank<=3、词长<=96及实际丢弃范围都保留；它是有限负结果，不能称15最短。旧15步／work128／peak13保持。[可提交四行文件](submission.txt)已由不同作者另写解释器、固定官方CLI全路径核验；没有平台上传或榜单比较。

[AI自写最终中文说明](native-documents/theory/r6-final.zh.md) · [AI过程索引](native-documents/theory/r6-final-process-index.json) · [完整模型/读取/计算回执](evidence/STARTUP-AND-PROGRESS.json) · [研究结果](RESULTS.json) · [完整公开过程包ZIP](PROCESS-BUNDLE.zip)。自写报告是当时捕获，后续原生终态以宿主完整回读为准。

|角色|实际node|实际model-task|终态|
|---|---|---|---|
|原生研究总负责人|ai-node-60ce43c0fdb954913d5cf32f|model-task-c2ea3667aa5aed3137ffee53ff8d2f2d|done|
|原生研究总负责人|ai-node-60ce43c0fdb954913d5cf32f|model-task-6094ccd810d80ae30ff9c006bceb9e64|done|
|原生研究总负责人|ai-node-60ce43c0fdb954913d5cf32f|model-task-2a5b8d3f21e2f0248f03f512492a24fa|done|
|理论方向负责人|ai-node-b912b62d9e95d94ddb26bfd6|model-task-2ed3e5bb0bea4f7e826102506ce40872|done|
|应用方向负责人|ai-node-0299a356d74db83b9ab4ebc7|model-task-5f7ea7b9088bdeac230a5604540b9d49|done|
|本轮独立官方CLI与全路径验收同伴|ai-node-22a9d6534cbf32a3d7d5029c|model-task-d72eded67cc42e86e4dc23dc047db011|done|

独立验收 `project-task-99f870b6bd681e7f0dccff953fb8bceb` 的210次验收调用中：新写解释器59、官方直接调用59、正式路径verify内部46、官方CLI46。含原实验91后，共 **301次验收**；与搜索一起由同一个持久硬账本拦截。保守已发租约140352／312，不退款，未闭合租约0；和真实调用数分列。全队硬帽2000000／50000。[逐producer预算](evidence/PROGRAM-BUDGET.json)及[原始计量账本ZIP](evidence/PROGRAM-LEDGER.zip)。

独立模型对实验摘要的review精确目标为 `M-faadd67bbdf57a62@1`。`@2`只将未完成深度的表述收窄，保留正文但**不自动继承@1复核**。路径验收另有 `M-110bcf615851324b@1`、完整逐状态/guard/CLI回执；搜索计数和逆字典未由另一作者独立重算。[复核原始范围](evidence/NATIVE-REVIEW-RECEIPTS.json)。

原应用负责人因预算参数包装错误保存了未执行记录；原ID查明未创建程序任务后，原总负责人在下一原生回合执行应用作者原封未改的冻结源。这个组织调整及一次新增验收同伴均来自团队实际选择。理论CI下界被应用队有理由拒作含M/S搜索的剪枝，但其精确小证书进入了独立验收程序。共享库的发布、全文读取、采用声明、源码依赖和复核分开留证；声明不代替运行。[采用与产物版本](evidence/ADOPTION-DEPENDENCIES.json)、[按需原文/代码读取](evidence/ACTUAL-SOURCE-READS.json)、[组织与消息元数据](evidence/WORKFLOW-EVENTS.json)。原始消息正文留在本机，公开为元数据与自写过程复述。

外部过程包c51ccae2的根MANIFEST及156文件、外部数学d2afe810的9个精确blob均已核验；数学目录根MANIFEST真实404已记录，未伪造。外部训练及旧宏收益保持原来源，不冒认本机发现；本轮没有同预算方法对照或加速声明。旧望月11页及全部原节点、记忆、停止、失败、预算账本保留，未倒填本轮论文阅读。旧12份POLICY/STATE哈希和原Git改动已核。[旧责任沿革](evidence/AUTHORITY-LINEAGE.json)、[工程失败及修复](evidence/ENGINEERING-HISTORY.json)、[Git保留核验](evidence/GIT-PRESERVATION.json)。

完整原生私有回执、消息、记忆和论文仍在本机；公开包只含自写稿、代码、路径、固定来源元数据和数学证据。输入ZIP提供相关源码/固定官方资源，完整原项目snapshot及映射继续留本机，不把子集ZIP声称为完整旧工程镜像。源捕获中的publication pending是写Git前时点；发布以包含本页的固定提交及宿主回读回执为准。

工程入口 WSL `archlinux:/root/projects/yohaku`。本轮目录 `diagnostics/native-mechanisms-20261117-01`，只读状态入口 `python3 diagnostics/native-mechanisms-20261117-01/observer.py status`。固定任务目标ID `native-mechanisms-next-20261117-v1`；重复任务应查原目标，不重新创建8回合。
