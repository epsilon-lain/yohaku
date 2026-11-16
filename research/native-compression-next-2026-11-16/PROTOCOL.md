# 概念压缩是否帮助找到更短比赛路径：原生复现协议

## 0. 状态与问题

本协议来自现有归档的静态阅读，不是新研究结果，不证明当前机器可访问或任何任务已启动。执行者为用户本机 Codex，研究者为原 Yohaku 持久原生团队；外部模型不得代替内部实验后回填回执。研究成果按用户已有授权整理后写入GitHub；本轮不上传比赛平台。

本包是用户明确追加的下一轮目标，不要求重复授权已有范围内的操作，也不授予重置旧phase或偷换封存限额的权限。优先利用现行有效准入；只有现场需要时才做独立追加阶段和关联。

目标分开检验：

| 问题 | 通过所需证据 |
|---|---|
| 找到更短的真实路径 | 相同challenge、初态、终态和动作规格下，新完整primitive路径短于预登记合法基线，并通过官方本地验证 |
| 共享宏帮助搜索 | 同预算配对的宏臂与无共享宏臂比较；包含全部案例与失败，不能仅挑成功例 |
| 理论解释 | 明确假设、宏接口与可验证命题／反例，能连到实际算法或产物 |
| 原生合作发生 | 精确正文读取、采用声明和后续产物依赖等证据；角色或共享库存在本身不算 |

保留所有primitive边、每个宏按展开长度加权时，完整路径空间的最短primitive距离不变。宏可能改善有界搜索的发现能力；不能凭宏名称较短推出数学距离下降。缩短既有见证只改善上界，除非另有完备下界证明，否则不称全局最短。

## 1. 现场恢复与准入（研究前必做）

### 1.1 历史锚点

固定历史run为 `native-theory-application-sol-20261116-01`。历史policy中的主机路径只是查找线索，不能当已确认安装位置：

`diagnostics/native-two-team-sol-20261116/run/`（相对于现场核实的Yohaku项目根目录）

| 对象 | 历史状态与精确身份来源 |
|---|---|
| 总负责人 | 持久节点；从该run权威登记读取node ID |
| 理论、应用负责人 | 首任务done；从登记及回执映射读取各自node/task ID |
| 总负责人收尾续行 | 历史快照running；从原队列、send journal与task receipt读取原node/task/request/thread/turn，逐一核对现场 |
| 原续行队列条目 | actor为总负责人，原任务内容是收尾核对；历史state为dispatched |

该续行只负责原阶段收尾和原回执核对；不得改写为本轮搜索。快照的60剩余turn、open状态、约19849剩余秒均为旧观察值。

### 1.2 最小操作顺序

1. 先只读确认现场源码、实际policy／STATE、registry、knowledge DB、队列、监督器与worker进程身份（PID加启动身份），记录UTC、版本和哈希。不复制归档覆盖现场。
2. 读取现场实现确认观察命令的副作用。归档 `manage_native.py status` 会调用activate并写CURRENT等快照；`start`可派发并启动监督器；`prepare_native.py`的build／stage_init会建立候选或状态，均不能当纯查询。归档 `inspect_native.py` 用普通sqlite连接，不是严格只读模式；独立读取数据库宜使用 `mode=ro` 和一致性读事务，不以此建立新库。
3. 用现场原生 `Control.node_status(node_id, request_id)` 或对应已核实接口查询上述原任务。unknown／pending时仅查同ID；保留原send journal、队列状态、费用责任，不重放POST或给旧ID换任务正文。历史`CURRENT.json`不能替代真实状态回读。
4. 在原任务有终态、完整output、commit确认、cleanup与进程回收证据之前，不为同节点再派任务。健康在途继续原工作；监督器若死，先区分worker存活、未知发送与可安全恢复观察，不能直接kill、Groups.close或重启重派。
5. 新用户目标在正常任务边界交给原root，使用全新、内容固定的幂等request。现场接口若仍如归档，可在真实环境通过 `Control(world).node_dispatch(root_id, new_request_id, user_task)` 走main仅派root的路径，明确记录为用户指令。此为接口形态说明，不是可直接照抄的启动命令。不要人工插queue或伪造actor绑定调用 `research_continue`。
6. 原root自主把工作交给原方向负责人。节点在真实任务中用 `research_continue` 提出自己的后续任务；宿主只消费其精确正文与原actor／task绑定。已有pending优先保留；相同请求只能恢复查询，不能换ID绕开未决状态。

### 1.3 阶段／模型边界

归档NativeGate会用policy SHA绑定STATE；6h从first_send_at起算，已知接口只有drain，没有reopen／renew。若现场仍如此且阶段过期或被drain，不能删DRAIN、清shared_stop、重置first_send_at、改旧policy SHA或重跑stage_init续命。保存并报告实际障碍；本轮用户授权可支持实现独立追加阶段桥，但必须保留旧阶段原样、节点沿革、记忆、在途责任和旧队列，不把旧任务绑定到新授权。桥要有明确新policy、剩余资源、负例及零推理准入验证，旧绑定与新绑定分开，无法可靠保留原节点则先停在此处，说明缺少哪个接口。

模型只用 `gpt-6.1-sol`；研究节点high／xhigh／max，root、方向及任何新增负责人必须max。fallback禁止，Astra禁止。检查实际目录提供的profile以及创建、派发、wake、continuation与最终wire-write门禁；检查线程回读。来源实际模型身份、token回报与实扣金额分开，未暴露的写unknown。不得改封存零推理副本中 `Connection.send` 的硬拦。

原thread的动态工具catalog参与SHA匹配：归档 `yohaku_codex.py` 仅在profile／上下文条件和catalog一致时resume，unknown或changed catalog会转新thread segment。新包是文件／代码资料，不是要求增加原生工具schema；尽量通过现有项目读写与 `task_submit` 调用验收代码，不为方便添加工具破坏原thread接续。若必须变更，显式保存旧thread、catalog hash、理由与新segment，不能清字段绕过检查或宣称仍是同thread。

现行额度、CPU／内存、并发和所有健康在途一起计入容量；旧64 turns、32节点、并发4、每任务1800秒／128工具和6h为历史初始上限，不是新额度。到界仅停新准入，保存结果和未完成项。

## 2. 继承证据与选题

先读各节点权威memory的真实revision，再 `math_search` 查摘要，按需 `math_read(id, revision)`；固定外部完整源经 `seed_index`／`seed_read`。外部Work、原生发现、本轮外部审阅保留各自来源。新上传的审阅报告只能标成外部审阅，不能倒填历史原生事件。

本准备包和验收脚本同样属于外部工程种子。先记录文件hash、来源、导入者、实际导入时间与run，再分别记录正文读取、声明采用和后续产物依赖。原 `seed_read` 只接受旧INDEX列出的精确固定URL；若现场仍锁定12个allowed source，本包不在其中，就不能假设任意新URL可读、偷偷换旧INDEX或绕过hash。可经用户授权的现有项目文件导入机制建立独立种子登记；若缺该机制，先做最小、可审计的追加导入桥，保留原来源集不变。正文未实际送达节点前不得记actual_read，脚本未被实际采用前不得预填adopt。

必须保留：

- 普通AC：`ac-08491`距离恰8，`ac-07445`距离恰13，不能在相同规格里要求更短；可用于动作实现与回归。ac-08491本轮原生成果为8条8步路径、work最低48；共享平坦宏64→55是批量表示成本。
- Stable：`sac-08491`10步、`sac-07445`15步为已知合法上界，尚无Stable最短性证书；普通AC下界不能直接外推。
- 旧8训练＋8正式的中性／负结果，以及后续开发题修订。旧正式失败 `ac-04359`、`ac-08327`、`ac-09594`、`ac-00104`、`ac-00399`、`ac-00974` 已曝光，若再研究应列开发集。
- 不可删证书与近2成本族等理论、合法宏接口、资源签名拼接扣除接点公式；按精确版本采纳，不预填采用事件。

由团队选题并说明理由。主实验只选在已有资料中没有最短证明、且能在测试前冻结一条合法primitive见证的题。这里“没有已知证明”是所检查资料的范围声明，不是全球文献断言。Stable的10／15步可作候选，团队也可另选未证最短的scored题。比较对象是我们固定归档的路径，不是当前排行榜。若没有可冻结见证，可另报“新增有界求解”，不能计算虚构的长度改进；不能给路径padding、改变同一比较的move spec／target或把未解题写成超长基线制造提升。普通AC与Stable分别登记，不能混算；选择Stable是另一类比赛任务，其10／15步最优性仍未知。

## 3. 测试前冻结的预登记

在首个正式测试任务发出前，以revision检查保存只追加版本的 `preregistration.json.tex`、`source-lock.json.tex` 和对应生成件。登记时应已有字段实值，不能留占位后补写：

| 字段 | 必需内容 |
|---|---|
| 身份 | run／阶段／node、用户任务request、版本、UTC、原阶段关联 |
| 官方来源 | 固定commit、manifest／move spec／core／CLI文件hash及实际获取方式 |
| 案例 | 精确challenge ID、初态、target、move_spec_version、scored、limits、各项hash |
| 数据划分 | train／dev／test列表与选择规则、历史曝光清单、排除规则；同一初态／等价派生／已知路径来源按组划分 |
| 固定见证基线 | 每题完整primitive路径、长度、work、peak、来源和官方验证；同一份基线用于所有比较 |
| 方法 | 完整两臂源码hash、宏字典hash、编译器与guard版本、启发式、目标球、去重／平局／停止规则 |
| 预算 | 每题每臂primitive计算上限、wall上限、内存、并行、预计算费、建库费和实际原生资源余量 |
| 重复 | 种子列表、案例顺序、臂执行顺序和重复次数；确定性算法说明不伪造统计重复 |
| 决策 | 主指标、成功门槛、失败／截断处理；测试后任何修订的新版本与开发身份 |

字典可以来自训练／开发轨迹、模型提出的规则及理论推导，但必须逐项标来源、构造成本和guard。test的已知解、反馈、轨迹、官方判定不能用于选宏、调参或挑最好种子。若需要先运行共同基线以取得见证，该步属于预登记前开发或独立锁定流程，并完整披露；不能用基线结果只挑宏易赢的题。基线来源和选样规则应先定，筛除无见证题的数量与理由也公开。

目标球等问题无关的共享预计算可用于双方，但必须同版本、只读并单列全部构建成本。依赖测试个案的目标结构／缓存不得只给宏臂，预计算也不得隐含已知test解。

## 4. 有／无共享宏的配对对照

至少两臂，具体搜索方法由团队决定：

- B0：完整primitive动作，不调用共享宏字典。
- B1：同一引擎、同一heuristic／排序／停止规则、同一primitive动作，额外允许冻结共享宏；macro边权为真实展开长度。

若研究目标需要两臂都允许“本题在线生成的局部宏”，可预登记共同局部宏机制，仅B1多共享字典，并另做primitive-only对照；不能事后改B0定义。正文写清比较的是“共享字典”还是“全部宏”。

每题同种子、同计算预算，primitive实现与检测／去重规则一致。宏内部每次实际primitive求值均消耗预算，包含中途guard失败、超界、重复、被丢弃的分支；预算不足以完整展开时不把半条宏当合法到达。跨臂缓存不能免掉一方计数。代码要输出可审计计数；CPU／墙钟／内存另报，避免把move计数称全部成本。

报告两个账本：搜索预算的同条件比较；包括字典学习、编译、预计算、搜索、验证在内的端到端成本。共享成本的摊销规则事先登记，同时给未摊销原数。官方复核、独立验证和新模型调用成本分别列出，不悄悄免费计入任何一臂。B1建库后仍给搜索同预算只支持“已有库时的搜索效果”；端到端公平需另看总账，不能自动称总体节省。

保存所有案例，按种子配对给出长度、work、peak、primitive calls、wall、状态、超时／截断原因。完整报告胜／平／负／双失败。B0未解而B1解，只能记求解收益；不能把B0长度当∞算平均缩短。二者均解的长度差单列，并注明筛选条件；样本太小不泛化。

## 5. 宏与展开证书

每个宏至少记录 `macro_id/version`、输入类型、适用条件／guard、primitive展开算法、展开长度和完整中间状态。参数化宏逐次实例化，宏名不能替代动作序列。若支持嵌套，依赖必须有限无环或有明确终止证明，展开器递归输出最终primitive；定义成本、引用成本与比赛动作成本各列。

证书对每一次实际使用记录：起点state hash、宏版本、参数、primitive moves、每一步约化后的状态／hash、端点、长度、work、peak、限制检查。完整路径从官方manifest初态独立重放，不能只验证宏端点或自定义消约。普通AC14动作与精确有序target `[[1],[2]]`；不得把符号置换／交换关系词当免费动作。Stable遵循自己的0..256动作、适用条件、rank限制和空target，逐步核验destabilize等条件。AC路径加`[16,15]`须在`sac-` ID下完整核验，不能计为同一AC解的免费步骤。

启发式词长剪枝必须披露，失败不推出无解。声明最短需要单独完备下界；带剪枝搜索、最短宏词或最优token切分均不够。

## 6. 官方本地验证与平台边界

先固定官方源。例如已审阅版本为 `SAIRcompetition/Andrews-Curtis@a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`。本轮若更新版本，先独立登记变更并重验基线，不能把两种动作／题目混在一组比较；本协议不替代执行时现行来源核对。

候选文件每行 `challenge_id: [integer_move_ids]`。从已校验checkout根目录运行的命令形态：

```sh
PYTHONPATH=competition/tools python3 -B -m verifier \
  --manifest competition/tools/verifier/data/manifest.json \
  --submission /absolute/path/to/one-candidate.txt --pretty
```

执行前核实现场CLI路径与hash；此处只给复现接口，没有执行。保存确切argv、cwd、Python版本、源／输入SHA-256、stdout／stderr、exit和UTC。顶层`accepted=true`只说明文件结构通过；每条还必须`results[i].ok=true`，读取其length、work、certificate_hash。CLI exit0、逐条ok和完整本地重放共同构成本地通过证据。

同一文件重复challenge时，官方只取首个成功路径，后续可能skipped。因此每臂每条成功路径用独立文件／调用验证，不能把被跳过项写成通过。最终候选文件每ID只留预定规则选出的一个版本，并另保留全部原候选。

本目录的 `validate_candidate.py` 和锁定registry是离线工程验收辅助，采用前核对真实文件、输入格式与hash，并把它登记为外部工程工具；其准备和tiny测试不算Yohaku原生研究。工具的基线应锁住普通AC13／8和Stable15／10的完整归档路径，普通AC08491使用work48路径。新题另行冻结合法baseline；工具输出也不能替代官方逐条回执或真实原生task证据。

本地CLI不联网上传，不消耗平台提交配额。平台账号、上传、官方服务回执、排行榜与成绩是另外的动作及证据，本轮不执行；未发生字段明确false／unknown，不从本地accepted推断平台成绩。可公开成果应整理到用户GitHub，发布的真实commit与哈希另记，不公开原始运行账户或聊天。

## 7. 原生协作、共享与污染控制

继续一个umbrella group、两个原项目scope的现实结构；不恢复旧A/B隔离规则，不规定增员、角色链或必须合作。数学定义、证明、代码、方法、失败即时进版本化共同库；组织／预算／调度留在项目档案。库对象以工具实际返回ID和revision为准，不编造可用ID。

分别留证：发布事件；摘要索引返回；精确正文读取；`math_adopt`自述；后续source@revision或artifact中的实际依赖；独立review和独立重跑。发布不等于阅读，阅读不等于采用，同作者第二实现不算独立同伴复核。记录选题／方法调整的前后版本、触发消息、未采用建议、取消重复工作与真实新任务；宿主修复和用户指定方向均标外部干预。

**共享库没有实验臂ACL。** 宏可被两方向和同一模型知晓，不能声称“模型认知上盲”。可复现的无宏对照应由冻结B0代码在独立状态中执行，禁止从库动态载入宏；它支持算法消融，不证明同一模型完全未受宏启发。无需为了实验另造隔离研究团队。

两臂用独立缓存、随机状态与输出目录；配对批次在一次已冻结离线任务中完成，期间不向任何模型回传中间test结果、改变代码或互读另一臂产物。该task完整返回后立即共享结果，保留真实返回时刻。若task中断已泄漏部分反馈，该样本转开发；剩余未触达部分能否继续须依预登记判断，不能一律重称全新测试。共享库／消息若泄漏test证书或调参依据，记录泄漏版本、影响范围；要么换未污染测试，要么明确仅有开发／事后比较。

## 8. 最小交付与验收

建议实际生成以下文件（名称可随项目规范调整，必须可由索引定位）：

1. `LIVE-STATUS`：现场身份、原root续行原ID回读、所有在途与准入判断、当前真实资源和阶段桥（若有）。
2. `preregistration`／`source-lock`：测试前的精确revision与hash、训练／开发／test和基线。
3. 两臂源码、字典／编译器、宏逐步展开证书与全部primitive候选；每项附原生node／task／source／snapshot／artifact hash。
4. 全量结果和配对表、搜索账及端到端费用账，包含失败、截断、泄漏和所有修订。
5. 官方本地逐条回执与可重跑命令，platform_upload=false；GitHub发布单独记录实际commit／URL。
6. 真实协作事件与依赖索引，权威memory@revision、开放问题、精确可续行入口。

一项“更短路径”至少满足：测试前冻结的同一合法基线；新路径primitive长度严格下降；同一官方规格和目标；完整合法展开；官方本地逐条ok；真实原生计算与产物回执。仅表示成本下降、work下降或找到宏短词不通过此项。宏因果收益另需配对结果，不能从一个成功案例推出。

若没有缩短，交付完整负结果／资源界限／可用理论或反例；若被工具准入阻塞，给出精确接口、原错误与现场保全，不以外部计算补成原生成功。允许原研究者自主完成或休眠，不要求耗完额度。

## 9. 本协议的静态依据

已阅读的本包相邻归档：`native465_review/FIRST-REQUEST.txt`、`POLICY.json`、定向摘取的`CURRENT.json`／`GATE-STATE.json`；两项目README与原launch handoff；`native465_public/README.md`、`RUNTIME.md`和官方CLI回执。接口依据是归档 `implementation/manage_native.py`、`prepare_native.py`、`native_gate.py`、`candidate/agent/yohaku_native_research_runtime.py`、`yohaku_shared_math.py`与`yohaku_ai_nodes.py`，以及固定官方 `competition/tools/verifier/README.md`、`cli.py`、`submission.py`。本次只读这些源码和JSON，没有导入或运行Yohaku宿主，也没有执行搜索／模型任务或官方验证。
