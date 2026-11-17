# 实际方法、共享与版本记录

2026-11-17，云端 `conjugation_frames` 子任务。根任务请求 gpt-6.1-sol/max；本小队继承根任务启动上下文，没有另启子代理，没有读取供应商计费或声称测得模型token成本。根任务已明确分工，不能把分工本身当成涌现、自组织或独立发现的证据。

## 实际阅读

启动后先读 `../SHARED.md`、`../PROTOCOL.json`；旧结论入口为 `../../proof_reconstruction_round2_20261117/README.zh.md`、`theory/README.zh.md`、`GOAL-STRUCTURE-NOTE.zh.md`。随后为接口、加载和既有表现读取旧 `application/run_experiment.py`、`theory/check_theory.py`、30文件源锁、官方 `core.py` 与 `stable_core.py`。后期只核对旧结果中0218的baseline与whole_object最终长度均18。未把旧 donor 四步或 `(y,x)` 删除机制当作本轮新成果。

所有训练原语访问都由固定旧20允许列表在字典成员过滤后索引；旧20本来已经看过，全部标为development。官方JSON解码、全文件hash核验会物化文件字节，但没有索引、打印、重放或分析新8及旧v1保留evaluation的动作数组。没有外部网页查询、平台访问、排行榜读取、比赛提交、原生Yohaku宿主连接或直接GitHub操作。产物由根任务统一审阅发布。

## v1：先做连续共同框架

首先独立把母题具体化为两个纯C共同框架隔着I/M段的配对合并：按槽计算净词，全槽相同才能识别；`B_h;P;B_g` 改成 `P;C_red(gh)`。编写 `frame_rules.py` 后把接口和SHA256 `c903775f783637b0fcc47d390ee30deaf0ac670662ba0204a2ecb31ba8349586` 发给 fragment_selection。对方随后消息报告逐字复制并纳入其v1开发/冻结范围；本组没有因此宣称对方已完成新测试或有收益。

review同伴在收到证明骨架后独立手算接受交换式，并确认单槽反例和资源反例的长度序；这是实际理论核读，尚不是代码/证书独立重放。

`FREEZE.json` 在第一次执行之前写入runner、规则、配置和协议hash。UTC 11:31:40执行合成：21个参数例、完整13→5合成证书及反例均通过；使用verification apply1248。UTC 11:31:57执行旧21扫描：0框架、0候选、0改善；search345、verification690。原产物原样保留，没有为了消除负结果扩大连续块的定义。

## 实际同伴提示与v2扩展

symbolic_rules同伴随后明确告知其冻结规则010/011为共同框架参数特例：010是 `[13,1,9,2,8]→[1,2,13]`，011还包含donor取逆标记交互。这个消息暴露出连续块识别器会遗漏的形状：取逆可分隔共同框架开启，末尾也可只关闭一个槽。

本组采用了该结构提示，新增独立文件 `pending_frame_rules.py` 和 `check_pending_frames.py`，以每槽pending词不变量给出一般兼容条件；没有改动v1冻结文件。v2要求每次乘法的目标/donor pending词严格相同，并要求非空共同框架确曾通过乘法；不加入symbolic组的I/M简化规则。因已收到特例提示，本组不称v2参数命中为独立发现；README与发根消息均明确和sym-dev-010同机制去重。

在编码v2之前告知根任务、review、fragment_selection版本扩展和费用累计。fragment_selection表示其v1已经准备冻结，不等本组v2；本组随后告知v2唯一真实边恰与其已纳入的symbolic010相同，不要求其更改冻结/测试边界。没有读取对方新8测试动作或结果来调参。

`FREEZE-v2.json` 同样在首次v2执行之前写入。UTC 11:35:21执行14个合成参数例、完整8→4交错开框Stable证书和单槽拒绝守卫，verification251。UTC 11:35:25执行同一旧21：仅0218有两个重叠候选，两个都省2步，work104优于106，因此接受一条，完整18→16；search352、verification704。07445无候选，保留15/work128。没有后续调参或重跑。

## 账本与复核边界

累计search697、verification2893、官方verify161次。`attempt-ledger.json`保留4个完成attempt及执行前后计数，费用包括两版重复扫描、所有诊断、期望中的D适用性失败及资源超限拒绝；没有失败的整轮运行、隐去重试或预算延长。所有官方apply都经一次wrapper计数，`stable.verify`内部也走相同wrapper；从源码看Stable apply并不递归调用AC apply，所以没有双算同一动作。

候选生成的符号约简/识别不计作官方apply；未测其总符号操作数、时间或token收益。候选实际展开与还原原语全部执行并计费。完整端点是自由约简后的精确有序tuple/rank，未按同构、共同共轭或生成元改名放宽。每个真实候选的完整新证书在原挑战初态官方验收，最终21例也再次官方验收。

已向review提供两版冻结hash、完整合成动作与状态、`review-input-v2.json`及唯一真实改善。其后收到完成回执并实际读取 `../independent_review/frames-certificates-review.json`：旧21例原/终按相同动作去重22条，加两合成4条，共26条路线全部逐状态/rank/work/peak与官方verify一致。review使用782次官方apply、391次独立解释器动作，另记review预算；本组没有重复运行它的代码，也没有把最终路线重放称为独立复现候选搜索。review另行解析接受pending不变量与逆序展开，并要求v2和sym010归一机制，已遵守。

数学、接口、合成、旧development结果分别报告：合成改进不算官方真实成绩；旧development不是新测试；相同规则的多次命中或多个小队实现不算独立机制；没有声称最短、一般AC解决、文献首创或原生自主系统因果收益。

根任务要求收尾后，本组停止新增实验与版本，仅补中文证明/README、独立复核完成说明、源锁副本、训练改善文本、最终 `summary.json` 与文件manifest。`summary.json` 的search697、verification2893已经包括v1+v2，不能再次把阶段数字相加；独立review782另属其预算。冻结的四个Python文件未为整理或可移植性更改；README明确其原源锁路径布局，保留本目录副本供全新布局复现。
