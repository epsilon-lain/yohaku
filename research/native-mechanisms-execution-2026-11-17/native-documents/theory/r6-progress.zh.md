# 第六轮阶段进展：真实有限实验已补，独立验收在途

【最终入口】独立验收现已真实完成并按原ID确认清理；完整最终稿见 files/theory/r6-final.zh.md.tex，过程索引见 r6-final-process-index.json.tex。下面正文是协调回合保存的历史快照，不把当时在途状态倒填为已完成。

此稿是证据协调检查点，不是最终结题。阶段 native-mechanisms-next-20261117-v1 不重置，原8回合/90分钟。宿主STATE首次准入1794919263.8307414，截止1794924663.8307414（北京时间22:11:03.831）控制授权；旧r6-start-checkpoint按稍晚reservation推算的22:11:04.787仅历史估计，不控制授权。

## 理论小命题与边界
原理论负责人已交 M-538c85aecd32c8d0@2：给定rank r≤8、指定槽 z^ε、其余旧关系词U_i在不含z的自由因子H中，实际入口是逐槽共同共轭C_g(S)。δ_A(g)为去掉g最长终端A字母子词后的前缀长度，m为非空旧槽个数。在仅允许单槽C/I、无M/S/其它D的修复类中，到指定删除D合法的最少前修复步数为 mδ_H(g)+δ_<z>(g)+[ε=-1]，再付1次D。残余frame、宏逐字费用及D实际重编号都不能省。
正文有自含证明、两个删除guard反例、负号/rank1退化及合成7步手核证书43work/12peak；经典自由积正规形来源明确，不是比赛纪录或全Stable下界。数学稿files/theory/round6-frame-deletion-boundary.zh.md.tex。应用已对精确@2解析限域review4680，root本turn另review5001；都不冒称程序复算。应用真实拒将C/I类下界用于允许M/S且无g/U见证的beam，没有代码采用或方法触发变化；不是合作收益。

## 从接口失败到首真实实验
旧应用模型完成了冻结而未运行：预算ID在旧worker包装层丢失，r6-app-runtime-fixture-v1查询仍unknown/replay_allowed=false；HOST明确无程序启动且已修复新worker的validator。旧M-8dcd6623caf5ee47@1未执行/非负实验说法保留，不倒填。
本root先查原ID、读完整冻结源/协议及其版本，再以新合法生产者执行，未改source_set8bdad4ae61955873477db5878e282e533dbd2e42b215f8cef2120ec7d0a60343。方法/代码署名仍原应用，root仅执行提交与汇总。
- 0/0夹具 project-task-44729ab486376ccf39736952c84cdbd4：done/exit0/cleanup，实际读meter公共context/decorator、核stable SHA234b164c…，只准备不叫搜索。
- 首研究producer project-task-89caab5017f4956aa52cef38be06d56a：done/succeeded/ended/exit0/cleanup/output_complete，snapshot与7产物hash均valid，issues=[]。
- allocate program-3ad0a623ab2690a2b074aa1b=600000search/6000verification，仅绑定本producer。可信reported=140329/91，保守issued=140352/96，无未决leases；cap不是实际耗用，unused issued不回收。

冻结方法为从官方初态全局精确Stable rank≤3结构分层beam+空目标逆B4，允许暂涨/真实S/D，不是旧两路径单调交换闭包、radius3局部窗或原路径固定DAG。无随机seed0；每rank宽512，长度≤96，深度上限10，590000调用/90秒停止，producer150秒。实际逆347态，层[1,1,3,26,316]；正向完整层1..8，之后90秒guard，9/10未完成，不从summary断言第9层生成数量。搜索140329=724逆+139605正，非法11826、长度剪枝857、beam丢弃99120，joins0/candidate_checks0。自报总耗时94.968955691秒含验收/CLI，不是方法加速比较。

## 候选与验收现况
无严格缩步，仍完整原语15/work128/peak13，路线[6,4,12,1,3,6,12,2,5,6,4,2,4,16,15]。本producer新官方CLI return0/空stderr/accepted，四行13/8/15/10、work127/48/128/50；同作者另写且逐动作meter.independent_step的解释器与官方全16态一致。它是不同实现，但不是独立作者复核。
已发表 M-faadd67bbdf57a62@2，@2仅澄清未完成层范围，与@1同一次计算不双计。完整选读范围、15动作/16态、新CLI全文和所有产物ID/hash在 files/application/r6-root-executed-evidence.json.tex。Root没有完整逐行读逆347态/独立复算，不把结构预览说成完整读取。

## 已实际派发独立作者
新同伴 ai-node-22a9d6534cbf32a3d7d5029c，原三个节点保留。request r6-independent-official-fullpath-acceptance-v1 / model-task-d72eded67cc42e86e4dc23dc047db011；actual running、gpt-6.1-sol/max、900秒/请求96工具；session 01a1e99f-c296-7ad0-a485-9f42f82889f6、turn 01a1e99f-c61f-70b3-bcaf-c4e8b00dfb3a。它获两项目grant，只在native-theory新增验收源码/action，不改应用冻源。要求0search/建议5000verification单producer，固定官方CLI+另一作者逐动作解释器完整验收，主要15步全路径与四行回归优先；不重跑搜索，不把有限失败升级下界。此时仍在途，不能预填验收通过或cleanup。
曾一次node_create试用root创建的既有记忆被明确拒绝，未起模型；后改为工具新建其专属权威记忆r6-independent-peer-memory.md.tex，才创建实际同伴；未重置原节点/历史。未使用的r6-independent-review-memory.md.tex只是准备文档，不是该节点权威记忆。

## 后续与公开边界
目前已用5/8，至少保留root最终1，另2不为耗额度硬用。本root不等待同伴；同伴保存实际验收后负责仅一次显式research_continue r6-root-final-after-independent-acceptance-v1。后续root按原ID核最终状态、读精确review/程序/预算与中文稿，保存中文最终入口；不新搜索/选题、不自动续行循环。私有记忆/原数学页/原始私聊不公开，外部c51ccae2/d2afe810与官方a0fd6e6f仍外部作者；旧v1排除动作保留。无平台上传、查榜或Git push回执。
