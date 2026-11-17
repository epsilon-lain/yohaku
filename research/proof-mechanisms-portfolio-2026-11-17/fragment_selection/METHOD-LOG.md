# 实际过程记录

本队由根任务指定负责固定证书候选图组合，模型请求为Sol/max；无子代理由本队另行产生。根任务安排的选题、共享目录和同伴联系是显式分工，不将其称为自主涌现或原生Yohaku续行。

1. 读取本阶段SHARED.md、PROTOCOL.json和旧theory/README.zh.md固定DAG/Pareto证明；参考旧application/run_experiment.py的官方blob核验、直接compile和apply计数模式。未读取旧v1四保留动作，未连接本机、比赛平台、排行榜。官方源码只从预存ac_official读取。
2. 实际向symbolic_rules、frames发接口请求，向review发同图定义、预算和审查请求。收到symbolic规则11条old_moves→new_moves后，读取并逐字保存rules-symbolic.json，hash `701b9b233a7ba0a1e926d0333ae8fef652e6c9bd83ab4a6ef12070bbd617e2bc`；接入发生在任何development运行前。对方提醒核心规则peak可上涨，因此保留逐步峰值过滤和完整证书验收。
3. 收到frames固定共同共轭块规则，读取并逐字保存纯生成器frame_rules.py，hash `c903775f783637b0fcc47d390ee30deaf0ac670662ba0204a2ecb31ba8349586`。本队最初编写的等价枚举器在开发前被该原样模块替代；固定采用v1双非空共同词范围。对方后来提供pending-frame v2，但当时本队已开始开发并承诺冻结v1，故没有接入；v2唯一旧真实命中与已接入sym-dev-010相同。sym010/011与frames同族，来源不算独立新机制。
4. 11:32:06完成第一次selfcheck，288次official search apply。11:33:02第二次selfcheck，另288次。第二次在已接入逐字frame模块后，把资源陷阱的“短前缀自身已超预算”弱fixture改为“两个前缀都合法、短贵前缀接后缀失败”，确认确实需要保留两标签；selector算法没有因此改变。第一份自检JSON被第二份成功自检替代，首次脚本hash/时间/288调用仍在正式ledger；不冒称首版源文件完整归档。两次成功的诊断调用全部计入576，不因复跑清零。
5. 11:33:22–11:33:23，只运行已看旧20及sac-07445共21例development。全部完成，search253648、verification937，没有失败或cap。统一原状态生成图，未根据选后路线再生成边。所有两选择指标相同。
6. 根与review分别阅读selector。review实查work入口一次、peak max、rank精确端点、同图hash、三维支配及贪心存活顶点定义，反馈无阻冻错误；强调平局不承诺move-list最小、图外无最优声明、负结果可接受。此反馈在冻结前收到并采用到报告措辞。
7. 11:34:22.963628写FREEZE.json，hash `0ede3d9a0018dffbf5b09c6cd17a8e682aac33de84e15402197d3be309898c5a`。锁定script `c026b4ea728db2338f5d3b5c5668decb26d7dfc94c3e3ed161d8c6a7d91aa6b9`、config、两规则描述/库、frame源码、官方源、根协议和已预选测试元数据hash。此前只读取新8元数据；公开训练JSON解析会物化所有数组，但不对新8动作字段索引、打印或分析。
8. 11:34:34.976之后通过冻结hash检查，先写TEST-ACCESS，再首次索引新8动作；11:34:35全8完成，search87872、verification328。0失败/0截断，greedy=DP；代码、配置、规则不再修改。没有按测试收益调参、增加样本或补机制。
9. 11:34:48运行report，无官方调用。之后根要求历史baseline比较。一次只读取旧development-results（它仅含旧4+07445）后用已授权20的键比较，报KeyError: ms-train-0009；该报告片段没有官方调用，没有改数据。随即读取旧round2 results.json，先核元数据恰好为获准旧21，才按baseline过滤；旧v1保留4不在输入中，没有访问它们。此零调用失败另存REPORTING-ATTEMPTS.json。增加compare_old_baseline.py仅整理历史比较与最终证书，不修改已冻结selector。
10. 报告后确认6胜/15平/0负；旧baseline总310→本轮296。根提醒不可把新库收益当DP收益，并要求新8所选边来源账。本队提供sym008在0389、0026各一边共缩4，普通原语在0094/0113/0281共缩12；写入README与机器观察结果，不作新增规则因果断言。向review发全部29例原初态、完整输出证书路径、冻结hash与计数，请其独立复验。
11. 收到独立review最终通过反馈：用旧独立解释器重算29图731边，全部精确端点/length/work/peak一致；原路径465动作、全部边展开1715动作；同graph hash与selected chain拼接一致。29例greedy/DP完整moves也完全相同。其去重47份原/最终证书逐态及官方verify通过，用1404次verification apply，独立记入review团队而非本队。报告为 `../independent_review/fragment-graph-review.json` 和 `fragment-certificates-review.json`。对方未重跑optimizer/DP，因此只称实现/证书复核，不称独立最优搜索复现。根另做其组合证书与CLI验收，不属于本队固定图对照，不回改本队results。

全部正式运行与任何错误都计入团队预算：search342096/1500000，verification1265/15000。本队实际无正式执行失败、无测试后代码修复、无图或标签截断。verification只有全局硬cap，未事后冒称每例硬cap预注册；每例search40000及图/标签/转移caps均在开发前写入config。

候选图只包括有限原状态端点的枚举宏库；无真实greedy-vs-DP差距，且本批DP最终每顶点只剩单标签，不能从抽象反例或程序正确性推出该宏库一定体现组合优势。没有新颖性、一般AC解决、所有路径最短、速度或token收益主张。
