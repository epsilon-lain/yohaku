# Yohaku 原团队第二轮中文进展

本轮已发生真实原生推理和研究计算。理论、应用两位原负责人均完成本轮所选问题；总负责人在收尾独立核验时超过单任务 1,800 秒，任务为 **error**，沿原 turn 只读查询为 **interrupted**。因此本轮不是“所有任务成功完成”。更新时间：2026-11-16T23:58:31.521696+08:00。

## 已保存的科学结果

理论队研究逻辑独立的布尔原子、平坦二元 AND 定义和带定义费用的重复描述，独立于比赛效果评价。得到精确公式 `C_D(T)=2(|T|−ν(D[T]))−1`；同一目标复用的全局字典阈值为 `2q` 与定义费 `δ` 的比较；收益次模恰在候选图分量为星或三角形时成立。P4 给出最小非次模实例和局部贪心半净收益的紧例，异质目标给出重叠字典反例。保留原子时添加确定性定义守信息，删除原子则有明确反例。详见[完整定义、例子和证明](docs/theory-author.zh.md)。一般证明获总负责人精确版本独立审阅（event921），有限数据没有被冒称独立同伴复算。

理论真实计算完成 1,099 个字典、32,767 个目标比较、26,376 项定义费优化检查，枚举 1,435,416 个字典候选，全部断言通过。计算佐证不替代任意规模证明。

应用队自主采用“旧路径前缀接口 + 有向桥接搜索”，三次真实搜索均**没有找到严格缩步路线**。首轮 111,595 次官方 apply，声明范围全部完成；随后 cap5 计算 76,016 次 apply，完整正 B4=28,511、逆 B5=6,081，空交，形成 **sac-08491 Stable 距离恰为 10 的作者证书**。秩界和条件双球推理获得理论负责人限域审阅；完整逆边实现、球数据及数值的独立复核尚未完成。最后 sac-07445 更深搜索 1,178,050 次 apply，逆 B6=130,799 完整，正球到预注册 350,000 状态帽截断；仍为合法上界 15，不能据此声称最优或不可达。详见[应用作者全文](docs/application-author.zh.md)及[后发文字勘误](docs/rank-text-erratum.zh.md)。

Stable cap5/cap8 两份结果的非执行 `limitations` 尾注残留“rank cap3”。实际冻结配置和球 metadata 分别为 5/8；原源、快照和产物均未修改，后发勘误单列。独立复核未完成的状态不会因复核条目数量而升级。

## 原生节点、模型与状态

|原角色|保留的原 node|本轮 model task|本地状态|
|---|---|---|---|
|原生研究总负责人|`ai-node-60ce43c0fdb954913d5cf32f`|`model-task-1830106e0e7e0223ad973dacd58c3da1`|error|
|理论方向负责人|`ai-node-b912b62d9e95d94ddb26bfd6`|`model-task-2424b2bfab9d4e99aeb86756f42afdd6`|done|
|应用方向负责人|`ai-node-0299a356d74db83b9ab4ebc7`|`model-task-8651f3dda6a052c0a635b977b4c2fb98`|done|

三个节点本轮均请求 `openai / gpt-6.1-sol / max`，原生线程配置回读相同；继续使用各自原 thread，未新增成员，没有 Astra、弱模型或降级。理论与应用均 `output_complete / commit_confirmed / native_cleanup_complete=true`。总负责人也已收妥文件并清理进程，但错误状态不能当成完成研究。请求、回读、原 turn、token 增量及完整公开回执见[模型回执](evidence/model-task-receipts.json)和[原 turn 只读查询](evidence/original-turn-query.json)。供应商底层实际身份及实扣费用未暴露，记为 unknown，不用配置回读替代供应商证明。

本轮目标作为用户指令 event482 / `user-round-20261116-02-v1` 登记；选题和方法由原负责人自行决定。没有宿主伪造 AI 续题，本轮两队均自行 `research_finish`。共享数学事件窗口为 (480, 966]；原策略 SHA 保持不变。剩余 turn 数并不解除 error 后的 shared_stop；当前禁止新准入，未重放旧请求或清除停止标志。

## 实际计算与比赛交付

|project task|实际 action|状态|
|---|---|---|
|`project-task-3628c3c7ed6347e97c261d4b4cca3528`|round2-inspect|done / exit 0|
|`project-task-ff723364534a087e5a4c80200f053268`|round2-pair-theory|done / exit 0|
|`project-task-c9c87a1852351c9edf11c3dae503cb7c`|round2-search|done / exit 0|
|`project-task-802847184ed0526eb3fa4966f91e216e`|round2-rank5-certificate|done / exit 0|
|`project-task-0996b6d2018bdfc65fb43b4deee6ad38`|round2-s07445-deeper|done / exit 0|

其中 official-semantics-inspect 是语义准备；其余四项为理论核验及三次真实比赛路线搜索，不把准备计作搜索启动。所有项目计算 exit0、输出完整、清理确认；“程序正常退出”和“搜索球完整”分别记录，07445 正球是截断的。完整原始结果、stdout/stderr、冻结输入和 SHA 见[计算及产物索引](evidence/artifact-index.json)。

固定官方版本为 `SAIRcompetition/Andrews-Curtis@a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`。官方 CLI 本地 returncode0、accepted=true：普通 AC 07445/08491 分别 13/8 步，Stable 对应 15/10 步；work 为 127/48/128/50。宏全部按原始 ID 展开，结果保留中间状态、资源和终点检查。普通 AC 已有旧最短性证明，本轮只回归，不重算旧构球。

[可提交文件](submission.txt)仍是冻结旧路线，SHA256 `a5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2`；[完整官方本地回执](local-official-verdict.json) SHA256 `793d179a5bff524505b44f081abeec197d2b49820d0a60f0e9c635d43db79399`。**没有新缩步、没有平台上传、没有查询当前排行榜**；与我们旧路径的比较和与排行榜的比较是两个问题。本轮没有运行同预算双臂宏优势试验，不宣称宏搜索因果收益；两个实例都是已见开发例，未声称无泄漏测试。

## 知识复用与实际组织变化

共享库先查索引，按需读取精确正文。理论实际读取外部定价种子 event663、采用声明 event698，后续冻结代码和产物确有该来源；新定理版本的代码/产物依赖另见 event740。应用复用旧资源组合契约 M-5606eba96406db45@1，实际完整重放全路径。新理论正文没有被应用队读取或用于比赛代码，不能把群摘要当成知识采用。发布、正文读取、采用声明、后续产物依赖和独立复核范围分列在[采用证据](workflow/dependency-evidence.json)与[原生读审事件](workflow/reads-adoptions-reviews.json)。

没有强制增员或固定流水线。理论完成后自行收尾，只为应用做了限域秩界审阅；应用将 rank3 有界负结果修订为另一个冻结 cap5 证书，再将算力转向 07445。总负责人消息强化资源验收，并发现尾注文字错误，应用实际读取后接受并后发勘误。总负责人提出独立实现核验，但在提交计算前超时；该帮助只有提议和部分准备，不算实际完成。详见[中文过程说明](过程包索引.md)。

## 保全、阻塞与公开范围

实际入口仍为 WSL archlinux 的 `/root/projects/yohaku`，Windows 对应 `\\wsl.localhost\archlinux\root\projects\yohaku`；使用原 stage 和原生节点。23,792 份旧档案通过保全审计；原 1,147 项责任全部保留，当前 1,148 项，旧负债金额未改、未退款或重置，见[审计](evidence/preservation-audit.json)。旧弱模型研究仍安全暂停且不持应用锁，没有被本轮唤醒。旧结果、失败、源版本、记忆和责任在用户本机保留，不对公开包删改旧研究。

**具体阻塞**：总负责人原任务触发 1,800 秒限额，原生 turn interrupted，原阶段 shared_stop 关闭新准入；未提交的 Stable 独立完整复核没有结果。两队已完成的研究和负结果仍有效保留，当前没有研究节点正在推理。后续若需继续，应先明确保留旧阶段责任的独立追加授权桥，不通过重置旧策略续命。

本公开包包含可公开数学、程序、冻结输入、完整科学产物和去私密回执；原始私聊、账户、凭据、权威记忆和带私有运行信息的完整档案留在本机。作者稿保留其写作时“待审/未公开”的时间状态；本页是后续整理状态，不能倒填为作者当时已发布。未做文献首创性声明。
