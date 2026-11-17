# 商图程序延迟执行的有限独立复核补充（桥02）

2026-11-17；复核者：理论方向负责人 ai-node-b912b62d9e95d94ddb26bfd6。本文供 lain-s-note 的中文审阅稿及 yohaku 的过程补充，由宿主决定公开；目前没有公开 URL 或 push 声明。

## 1. 结论及证据层次

复核对象是 root 的新数值结果 **M-57835ea93dc9d121@1**，对应完整冻结代码 **M-acabf7d31997c9bc@1**，解析依据 **M-2425cab292392fd9@1**。本次结论为：所读源码覆盖与冻结范围相符；主要断言表达了对应命题；真实产物身份、全部计数项及所选字段与回执相符；独立手工核对了全部覆盖基数和 n≤2 的计数。未发现本范围内的矛盾。

这不是完整独立程序复算。本人没有写第二份实现、提交新计算、重新运行 root 的约154万次距离检查或本人的 pair-AND 实验。以前 review1377 是一般证明的解析复核，不据此宣称旧数值已经验证；本次是另行源码审阅、真实产物读取和小范围手算。作者程序的有限枚举、同作者两种算法、同伴源码审阅及独立重跑四者不混同。

## 2. 实际读取与锁定身份

已实际全文读上述新结果和完整代码数学条目，以及当前权威源码和冻结文件：
- files/theory/round3-root-quotient.py.tex@a88addefcacdabc95fc3dbf319f8199e25bdaeb31599f3639034ea8be6d43bf4；生成 SHA256 da2a3674295c59db460b4f5f1ac87addbb26f4ed1576464a11bc138606ef827e。
- files/theory/round3-root-quotient-freeze.json.tex@dc4507a4ee4d5ae7ec2f82d38a279663f425b43e6705a4986cfb3cef099ff5ce；生成 SHA256 8e69c202fa177d8e6e0eee7f36c1bddc9c66655d4ccb86106aa55404eb7ded0d。

实际查到的新任务是 project-task-24e34a0dde1b1bd250763d7a99875d52，request 为 round3-root-quotient-delayed-execution-bridge02-v1，action 为 round3-root-quotient。snapshot/source_set 为 c0e58442b566c2d83a6f87654c82a22f031543810b9f370caeec9ea95557079b。task_status 显示 succeeded / execution ended / exit0 / cleanup_confirmed / output_complete；provenance 的 snapshot_valid、artifact bytes_verified 均 true，issues 为空。provenance 工具的 executed=false 表示此次查询本身不执行程序，不否定其中已存在的执行回执。

产物 round3-root-quotient-results.json，4655 bytes，SHA256 58a8be084120d21f97c4a875c2a036e32275aef96db74e91261b39faa4e6b371；稳定 artifact ID 为 artifact-017a43ef36fe7217255fb2bdb84e12db46edc00252b853c5da6f4b750fee4e01。实际按 JSON pointer 读取 /counts、/counts_by_n 的四行、/first_spurious、/explicit_counterexamples、/limitations、/scope、/dependencies。所读计数项无后页；这不是逐字读取整个原始 JSON 或逐实例证书的声明。

当前 manifest revision cd46a2cf67bf63b72c0989e9ed273cc5f063f72361a5f78110a5f6dfc90f80ae 与快照一致；对应 action 是 kind=python、entry=round3-root-quotient.py、args=[]、timeout_seconds=120。此次只读，未改 manifest、源码、冻结协议或停止记录。

## 3. 源码覆盖及断言审阅

1. n=1..4；每个有序异顶点对独立取边，故遍历全部有标签顶点的无自环有向图，每图一次。这里没有动作标签或资源历史；源码标题中的 unlabelled 不应解读成只遍历无标签图的同构类。
2. partitions 由首项0、后项0..当前最大值+1的 restricted-growth word 枚举，每个集合分拆一次。商邻接是各原像点邻接像的并集，保留商自环。local 比较各点的后继纤维集合与整个纤维并集，正是局部可提升条件(L)。
3. 所有起点、所有商目标子集（含空及全体）均比较原图到其饱和逆像的距离与商距离；一般断言商距离不大于原距离，local 时断言相等。BFS 正确处理商自环；n≤4 时有限最短距离至多3，所以 INF=99 不会与真实有限距离冲突。
4. n≤3 的 walks 枚举长度0..4的全部行走，允许重复顶点/回路，并不只列简单路。具体行走按商路线收集末点，与 forward 的实际末点集合比较；local 时再断言非空。调用者确保路线首项是起点像。
5. 对每个商行走又枚举全部实际目标子集，backward 的前驱集合与 forward 可达末点作起点成员等价检查。它不是只核饱和目标；也不是声称一次独立算法已重建整个前驱集合的逐元素证书。外层所有起点提供相应各源点测试。
6. 三个显式反例的实际边表及断言分别检验单步伪路线、中间代表不相容、目标不饱和时的距离差，逻辑与新产物相符。
7. by_n 使用 Counter 差，零值键会被省略；例如 n=2 未列 strict_optimistic_distances，不能解释为漏跑或未知。冻结文件在此代码中用于报告，真正循环上限写在源码内；本次逐项比对相符，但未来只改冻结 JSON 并不会自动改变执行范围。

这是真实源码逻辑审阅，不是每条断言的独立运行时轨迹证明；未额外检查宿主解释器内部实现或未暴露环境。

## 4. 独立手算一：全域覆盖基数

记 S(n,k) 为第二类 Stirling 数，B_n 为 Bell 数。由循环结构，每层图数 G_n=2^{n(n-1)}，图-分拆数 G_n B_n，距离断言数
D_n = n G_n Σ_k S(n,k)2^k。
其推导不依赖作者的输出计数。

|n|G_n|B_n|G_n B_n|Σ S(n,k)2^k|D_n|
|--|--:|--:|--:|--:|--:|
|1|1|1|1|2|2|
|2|4|2|8|6|48|
|3|64|5|320|22|4224|
|4|4096|15|61440|94|1540096|

合计4165图、61769图-分拆、1544370距离检查，与实际产物逐行吻合。该闭式检查验证枚举覆盖基数，不独立验证每个距离值。

## 5. 独立手算二：n≤2 的全部计数

n=1 只有空图和唯一分拆：local=1；距离检查及相等各2；具体行走、商路线、local路线各1；目标前后向检查2；无严格距离差或不可提升路线。

n=2 有空图、仅01边、仅10边、双向边四图，及单点分拆/合并分拆两种。单点分拆总满足(L)；合并分拆仅空图和双向图满足，故 local 图-分拆数6。距离检查48；local 相等数为4×2×4 + 2×2×2=40。单点分拆是原图，合并分拆仅有空/全目标，因此严格距离差为0。

长度0..4具体行走在四图上的总数分别为2、3、3、10，和18；重复两分拆为 raw_tree_walks=36。单点分拆的商路线18条；合并分拆为空图2条、另三图各10条，总32，故 route_endpoint_checks=50。local 路线18+2+10=30。每条路线对4个实际目标子集测试，故 backward_target_checks=200。每个单向图的合并商有自环：无后继起点的长度1..4均不提升（4条），有后继起点长度2..4不提升（3条），两图合计14条。这与实际 n=2 全部计数一致。

n=3/4 的 local 数、严格差、全部路线及前后向数，仅审源码和读取作者真实汇总，没有独立复算。不得把上述手算扩大为154万次逐实例独立复核。

## 6. 可追溯边界及保留

新产物总计 local 图-分拆12709、local距离相等429858、具体行走5797、商路线7713、local路线2461、前后向目标检查61498、不可提升商路线2909、严格乐观距离67680。这些超出上述手算范围的总数仍标为作者运行结果。

旧源、旧 GateStopped/source-conflict/stop 及预算沿革保留；新桥授权后的成功不回填旧请求。本人的 pair-AND task8af630 已完成但本次没有重跑。外部框架/宏接口在作者依赖表仍保留 external 身份；读取它们在本产物的引用不等于重新读了那些外部正文或将其改称本机发现。本文实际复核依赖是三项精确版本和所列真实源码/回执。

本补充不涉及官方AC合法性、比赛距离、时间/token改善、费用、通用求解能力或文献首创。不改写 Stable08491 后续外部完整复核为本机原生发现。有限核验支持而不代替一般证明。小复核到此完成，不重开数学主线、不请求新计算。

## 7. 本次留证登记

本有限审阅另发表为 M-2763b2dcafe3dd4f@1（writing_event1843，发布本身不是验证）；对新数值版本 M-57835ea93dc9d121@1 的 review event1841 明确标注 verified_source_coverage_and_manual_n_le_2_counts_only_not_full_independent_rerun。此前一般证明的 review1377 不被修改。本次枚举允许有向回路，只排除原图自环；商自环保留。全文读取、实际采用、独立复核和作者原生计算回执分别登记，不能把任何单一登记当作其他三项。
