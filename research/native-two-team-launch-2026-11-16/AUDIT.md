# Yohaku 原生研究启动接续审计

审计日期：2026-11-16。结论：归档包含真实 Yohaku 原生节点、Codex worker、项目计算、消息、记忆和版本事件接口，具备最小实现基础；**现有配置不能直接启动用户要求的新研究阶段**。此次只读审计归档并写本文件，未调用模型、未控制原宿主进程、未改旧账本、未更改封存副本。

## 1. 证据范围与状态边界

- 可直接核对的源码事实来自 `process_review_20261116/implementation/`、`process_review_20261116/host-implementation/`。
- `two_teams_sol_20261116/HOST_HANDOFF.md` 与 `REGISTRATION.json` 均明确该两队研究是在 ChatGPT Work 协作环境完成，原 Yohaku 宿主未挂载。这些成果应继承，但不能当作 Yohaku 内部团队、任务、模型迁移或持续运行的证据。
- 本审计不把归档源码等同于当前宿主已安装源码；没有读取远端现行仓库，没有将远端实现推定为本机实际运行版本。实施前须在真实本机取得源码、生成件、二进制、配置和进程身份的 hash 回读。
- 父任务转述的最新零推理联调：真实 worker、新 thread、`gpt-6.1-sol/high`、600 秒、零工具；`Connection.send` 在 `stdin.write` 前无条件硬拦 `turn/start`，推理数为零。此记录仅作待本机原件核对的预发送验证。**不能算研究启动或研究首回执**。
- 本归档 `yohaku_codex.py:200` 的 `Connection.send` 尚未包含上述无条件硬拦；因此绝不能复制归档 send 实现覆盖最新封存副本。二者是不同版本，必须分别封存与标识。

## 2. 已存在的真实接口

| 职能 | 归档接口/文件 | 真实持久证据 |
|---|---|---|
| 节点身份 | `yohaku_ai_nodes.Control(world, actor='main')`；`node_create(request_id, role, task, memory_source, profile, project_ids)` | `files/ai-nodes/registry.json.tex`；`created_by`、固定 node_id、profile、project_scopes、memory_origin；创建本身不推理 |
| 任务派发 | `node_dispatch(node_id, request_id, task, profile=None, ...)` → `yohaku_codex_tasks.Control.start(..., node_context=...)` | 节点任务索引、确定性 host_request/task_id、Rust/Loom chat 请求、私有任务记录；先持久预留后 launch；同 ID 不重放 |
| 原生研究执行 | `yohaku_codex_tasks.run_task` → `yohaku_codex.run/_run` → `yohaku_codex_linux.launch` | 真实 Python worker PID/start、原生 app-server PID/start、thread/turn ID、诊断和原生事件 |
| 模型确认 | `ai_node_models(provider='openai')` / `catalog('openai')`；`model/list`；thread/start 回读 | 可执行 reasoningEfforts、选定模型、`model_settings`、thread 返回 model/provider/reasoningEffort；catalog 不证明推理额度 |
| 节点查询 | `node_status(node_id, request_id, cursor, max_chars, wait_ms)` | Rust chat 状态、model_phase、output_complete、receipt、usage、memory_versions；unknown 不允许新派发 |
| 消息与群聊 | `chat_create`、`message_send`、`messages`，对应工具 `ai_chat_create/ai_message_send/ai_messages` | 真实 sender、消息 seq、reply_to、task provenance；纯消息不启动模型；wake 会派发 |
| 记忆 | `ai_node_memory_read` / `ai_node_memory_write(revision,text)` | 整个 `.tex` source revision、实际读取版本进入 task.memory_versions；写入需 revision 检查并 Loom 回读 |
| 历史与压缩 | `ai_node_history` / `ai_node_compact` | 原完整事件和归档保留；同 durable node_id、新 generation/上下文；需已知空闲/终态 |
| 项目授权 | `yohaku_project_sources.Projects(world).register(manifest_source)`；`yohaku_node_workspace.project_scopes` | `yohaku-project/1` manifest、项目版本；后代只能继承或缩小项目 grants |
| 离线计算 | `project_plan`、`task_submit(project_id,action,request_id)`、`task_status`、`task_result_index/read`，以及项目输出工具 | 独立 project-task ID、输入 snapshot、原始日志/结果、沙箱与 cleanup 回执；不是模型工具自述 |
| 运行群组 | `yohaku_experiment_groups.Groups.configure/bind/inherit/status` | 私有群组 journal、节点归属、dispatch 累计、在途与清理状态 |
| 共同数学库 | `host-implementation/immune_runtime.py` 的 `Knowledge` 与 `math_search/read/publish/challenge/review/adopt/lease` | SQLite entries 各 revision、body_sha256、来源节点/任务、events seq；发布/独立复核断言/正文阅读/采用分列 |
| 接续请求 | 同文件 `research_continue` / `research_finish` | 模型自主选择的下一任务队列与 finish 原因；宿主 drain 队列不应自行选数学任务 |

`node_create` 的声明 role 只是责任文本，不能据此认定自主组织形成；应关联实际后代创建、任务、消息、版本读取、修改与产物。

## 3. 当前不能直接启动的具体阻断

1. `implementation/BATCH-PROFILE.json` 仍是 `adaption/gemma-4-26b-a4b-it/none`。`yohaku_ai_nodes.validate_profile` 把不同于默认 profile 的模型锁到特殊 mixed helper 授权；单运行 `two_teams_sol_20261116/model_policy.py` 不会接入这些路径，也不会更改真实模型。
2. `yohaku_research_models.py` 仍为 Adaption 研究节点 catalog/selection，不能用其 UI“当前模型”来证明新 Sol 原生节点配置。需要新阶段专用 OpenAI 路由和实际请求回读，不改原全局账户选择。
3. `immune_runtime.actor_context` 要求 `node['profile'] == c['profile']`，`wrap_tools` 也拒绝不同 profile。这禁止同时采用负责人 Max 与协作者 High。其财务、send_admit、公平排队钩子绑定 Adaption POST，不足以约束 native Codex `turn/start`。
4. `yohaku_sol_seed_gate.SeedGate` 是固定 3 人、8 turns、48 tools、2700 秒且严格 Sol/high 的既有种子阶段；`ai_nodes.task_tools` 在该阶段删除 create/dispatch 等工具。不能把它当作可自行发展两队的组织引擎，也不能为了新阶段而解除其封存保护。
5. 旧 `yohaku_workflow_gate.Gate` 有历史实验 ID、人数、深度、POST 和费用的硬编码；不存在任意新“两队”policy 即可兼容的证据。若采用新 format，须新增显式适配分支与新阶段 gate，不能复用旧 ID 或伪造旧授权。
6. `host-implementation/manage.py.activate(live=True)` 清理既有多组环境变量、设置旧 profile/资金与 immune 配置，并将 `YOHAKU_NO_MODEL_REQUESTS=0`。`manage.py start/serve` 不可原样用于本次接续。
7. `Groups.close()` 与 watcher 会取消已派发模型和项目任务。**它不是“停止弱模型新 dispatch、保留在途”接口**。旧 supervisor 的 finally 同样调用 close，直接发信号停止它可能触发在途取消。
8. 旧 supervisor 在负责人空闲时无条件生成 `next-...` 续行请求。这是宿主中性接续，不能记作模型自己选择任务；新阶段优先只消费研究者显式 `research_continue` 队列。
9. 原两 A/B 群组隔离会拒绝跨组 node/status/chat/message 访问，尤其不能直接用其 wrapper 实现两队相互通信；它还按 `files/group-A/B` 收集组织版本。用户当前是共享数学的理论/应用两队，且不是原独立对照，不能无声承袭原隔离/固定组织条件。
10. `Connection.send` 是最后可验证的 native `turn/start` 发送边界。新阶段的每次 turn 均需在那里执行当前阶段准入、模型下限与不降级检查；只在 node_create 时查一次不足以覆盖 dispatch、wake、未来续行和上下文重开。

## 4. 推荐最小实现路线（新阶段、新副本；不碰封存零推理副本）

### 4.1 先保全、再建立新阶段

在真实本机只读记录旧实验登记、supervisor PID/start、节点最后 request/task、Rust chat 状态、私有 task records、在途 request journal、SESSION-LEDGER 和已有 source/配置/二进制 hash。快照保留所有原 ID、原费用责任、未知状态与原负责人。

为旧弱模型路径增加或启用**仅阻止未来准入**的持久标记（建议新阶段控制字段 `new_dispatch_allowed=false`，名称为建议新增，并非现有接口）。将旧 supervisor 调整为 drain/observe：停止 initial/next/queue/wake 的新派发，保留已在途 worker、只查询原 request ID。不要调用 Groups.close，不要退出会自动 close 的 finally。对在途结果未知的 POST 不重发、不过户、不退款。新阶段与旧阶段同在途时，资源容量按机器真实占用计算。

创建独立 candidate/world/home/阶段登记；在新登记中绑定旧快照与研究种子的 hash。不能复用已关闭群组、已固定 profile 的创建 request ID、已封存 policy/state/turn 记录。原始账本只是被引用/保留；Codex 会话的授权和计费不能用旧 Adaption Credits 虚构换算。

### 4.2 新 native gate 与 profile 策略

建议新增 `yohaku_native_research_gate.py` 和专用 pinned policy format；这些名字是实现建议，当前归档没有此模块。通过现有 `yohaku_workflow_gate.Gate` factory 显式按新 format 选择新 gate。必须实现被 Control/task_tools 调用的准入、reserve/create/start、任务上下文校验、事件与终态接口；不冒充 seed_stage，不设置触发 Codex 删除节点工具的 mixed 标记。保留 legacy/SeedGate 的行为和原 file hash。

新阶段默认 `BATCH-PROFILE.json` 和节点 profile 为：

```json
{"provider":"openai","model":"gpt-6.1-sol","reasoning_effort":"high","budget":{"timeout_seconds":600,"max_tool_calls":null}}
```

600 秒仅是首阶段可明确验证的建议参数，不是用户指定的永久硬限；真实研究可按用户授权资源与实际机器另行配置。节点工具数不能从零工具联调照抄为 0；否则不能产生原生研究组织。负责人 profile 在同一结构中明确选 `max`。若实际本机 catalog 不支持 max，则停止负责人派发并报告，不自动降为 high。研究模型只允许 Sol；实际 catalog 可执行的 high/xhigh/max 均不低于 floor；Ultra 仅在本机产品确实提供并能验证时选用，不能作为 API effort 字符串硬填。

把 `validate_profile` 改为“新阶段固定 Sol、允许受控 effort 集合、负责人 node ID 由宿主钉住 Max”的策略。检查点至少包括 node_create、node_dispatch、message wake、队列接续、run_task 最终 chosen profile 与 `Connection.send(turn/start)`。openai 父节点创建后代时当前实现并无通用强制继承同 profile；不要假定 Max 自动向后代继承。后代显式 High 或以上、scope 不扩大、权限不扩张，禁止弱模型 fallback。新阶段的 config/ai.json 也设为相符的 codex-local/Sol/high，避免旧生成配置混入。

不要修改账户、不要复制凭据到研究 world、不新购额度。只使用现有 `runtime/CODEX-DEVELOPMENT.json` 所指本机授权入口，通过 `YOHAKU_CODEX_LINUX`、`YOHAKU_CODEX_AUTH_HOME`、`YOHAKU_CODEX_PROVIDER_FILE` 的现有机制引用；实际目录值不公开输出。先只读确认实际 executable hash、模型 catalog 与权限 profile。需要的登录能力不可用则停在本机接续条件，不把 catalog 成功当付费推理成功。

### 4.3 真正的研究队与两队结构

用户要求先在 Yohaku 内建立 AI 研究队，再分理论/应用两队。严格实现可先建立一个**原生持久研究负责人节点**，给它用户已确定的两队方向、共同种子和原生工具，让它在新阶段授权范围内亲自调用 `ai_node_create` 建立理论/应用负责人并形成任务/消息记录。新阶段 gate 可依据已批准的两团队方向绑定其 Max 身份，但不替它选择数学子问题、角色数量、复核程序或具体 workflow。不能由 ChatGPT 协作代理代替这些 native 调用，再回填 Yohaku 节点 JSON。

最小连接方案：一个 umbrella `Groups` 实验群组承载整个研究队，两个 `yohaku-project/1` 项目分别承载理论/应用文件，根负责人获两个项目 grants，后代按任务缩小；团队归属另存版本化元数据。此方案保留现有 same_group 消息与 stop 权限，避免复制 A/B 跨组禁通信规则。需要共享数学服务时，在服务 actor context 中区分 stage/group/team，team 来源必须由真实 node/project 绑定，不让模型自报 sender。若选择两个 host group，须另实现可审计的纯消息桥与共同库，不能声称现有 wrapper 已支持。

外部只规定用户已决定的目标、模型范围、权限、资源与如实留证。研究者自行决定是否增加同伴、如何分工、向谁提问/复核、使用何种方法及何时修订。不要继承上一 ChatGPT sprint 的“每队最多一个助手/固定 observer/固定 sprint”作为本机用户要求；如因资源需要设限，登记为新的外部限制。

### 4.4 共同数学库与种子导入

复用 `Knowledge` 的版本化数学数据/事件语义，而非复制整个 Adaption immune wrapper。新阶段 wrapper 绑定 native task/node 与新 gate；允许不同受控 Sol effort，保持项目授权和真实工具调用链。保留 math_search 摘要、math_read 正文、math_adopt 自述、math_review 独立断言以及后续产物证据的区别。

两队得到同一份入口：`two_teams_sol_20261116/shared/SEED.md`、完整 `shared/MATH_LEDGER.jsonl` 和 snapshots 索引、两队 CHECKPOINT/README/RESULTS、应用证书/代码/核验回执、观察报告与历史提交固定版本。**SEED.md 只包含较早的 ac-08491=8 等结果，不含本轮完整新成果，不能只导入 SEED 造成知识倒退。**导入完整应用 checkpoint 的 ac-07445 普通 AC 距离 13、Stable 合法 15 上界与其证据边界；导入理论图族结论、有限核验和未解决范围。

导入项逐项保存原路径/sha256、原 surface、作者/审阅声明、原数学版本与导入时间。ChatGPT 研究与复核不改名为 Yohaku 原生完成，不补造旧工具事件。旧 checkpoint 的 next task 是候选接续而非已执行事实，新节点可以依据新授权自行选择。共同库允许数学内容与方法、代码、反例和失败；组织策略留在各队项目，但不应为了旧 A/B 隔离阻断必要的数学沟通。

## 5. 可验证实施顺序与通过条件

| 步骤 | 本机操作/观察 | 通过条件 |
|---|---|---|
| 1 保全清单 | 只读旧 registrations、supervisor 身份、节点/task、账本、未知 journal；计算 baseline hash | 未重置/覆盖旧 ID、余额责任与源文件；有新阶段 lineage manifest |
| 2 停未来弱 dispatch | 启用旧路径 future-admission block，supervisor 只 drain/query | 之后没有新增弱模型 request/turn；原在途 PID/start 与原 request 可继续查询；没有 close/cancel 副作用 |
| 3 新副本审查 | 核对实际源码/`.tex` 生成对、二进制、DEV/config、new gate/policy hash | 封存副本及其无条件 turn/start 硬拦字节完全不变；新运行入口与路径独立 |
| 4 离线负例 | 以假 transport 捕捉 stdin；覆盖弱模型、low、unknown effort、fallback、旧/闭阶段、scope 越界、重复 request、wake/queue | 所有非法 turn 在 write 前阻断；重复不新发；pending/unknown 原 ID 查询；无真实模型请求 |
| 5 原生无推理接线 | 使用新的独立 fixture，真实 task worker 到 thread/config/工具绑定；send 硬拦 turn/start | 真实 worker/模型参数确认，工具目录含节点/通信/记忆/项目/数学服务；推理 0，标明不是研究启动 |
| 6 允许新阶段真实准入 | 仅新运行副本、已授权新 policy，从全新 root node request 开始 | 模型/effort/profile 与 native thread 返回一致；turn/start 真实发送获 turn ID，不触及封存副本 |
| 7 首完整任务回读 | `node_status(root_node, original_request)`、私有 task record、node-events、Rust chat、生成文件 | done、output_complete、commit_confirmed、native_cleanup_complete；task/node/thread/turn 与 requested/confirmed model 链一致；有实际回复/版本产物 |
| 8 两队成立回读 | 根节点的 create/dispatch/chat/message 原始调用及目标 nodes/tasks/memory/project scopes | 两负责人由原生根节点实际建立和分派，后代至少 High、负责人 Max；存在各自真实 task 与输入版本，不只 role 标签 |
| 9 持续观察 | 同原 task ID查询、队列处理、事件前缀快照、文件 revision、后续产物 | 明确观察窗口及截止前缀；无事件不补填；宿主工程操作、外部限制、模型决定分列 |

步骤 4/5 是实现准备，不发送模型；本审计未执行以上验证。正式启动的必要实现/本机证据不齐，不宣称已运行。

## 6. 首回执判定与组织观察

“进程 launched”“目录创建”“thread/start 成功”“配置写了 Sol”“已到 send 前”“零推理 final 文本”均不能作为研究首回执。至少需真实准入的新阶段 turn/start 已发送且服务返回 turn ID，随后实际原生终态、内容、commit 与 cleanup 全部闭合。只有配置/线程回读时，准确称“请求配置及原生线程确认”；供应商实际模型或 token 未暴露就记 unknown，不能自填。首个完整根节点回执只能证明研究队开始执行；“两队均启动”还需理论/应用各自至少一个真实任务的同等级证据。

原生 `.node-events.jsonl` 已记录 `submitted_context`、`native_tool_catalog`、`native_thread`、`host_input_snapshot`、`native_event`；结合 wrapper 的 `tool_completed`、`worker_tools_bound`、`file_version_observed` 和 node registry/task private records，能观察真实任务/子节点/通信/记忆。新 wrapper 应在所有创建、派发、消息、记忆、数学工具前后记录请求与结果，并保留 idempotency 关系；异常也记录，文件观察不只扫描旧 group-A/B。

采用链至少区分：检索返回摘要 → 正文版本读取 → 研究者声称采用 → 后续源版本/代码/论证实际引用或执行 → 独立复核断言与其证据。组织变化至少需要“何种实际困难/反馈触发 → 谁请求/执行改变 → 后续任务/消息/产物是否随之变化”；仅改标题、增角色或写组织总结不足。外部观察者的复核和宿主修复不能记为团队自行演化。

## 7. 交付给本机实施者的阻断清单

- 未取得本机源码与 latest sealed send 原件/hash：不得覆盖归档版本或启动。
- 旧 supervisor 停派发会触发 finally close/cancel：先实现 drain，不能直接 kill。
- 原有授权/模型 catalog 不可用、Max 不可执行、存在 fallback：暂停新派发。
- 仍用 Gemma 默认、Adaption 研究 model bridge、三人 seed gate 或仅校验脚本：未实现用户要求。
- 不能从 native 根节点真实创建两队/观察工具事件：不得用 ChatGPT agents 替代。
- 新阶段 turn/start 未挂最后发送准入、scope/模型/phase 校验：不得上线研究。
- 需要拆掉封存零推理副本的硬拦才可运行：路线不合格；建立独立新阶段运行副本。
- 只有预发送/零推理联调或启动 PID：继续标 prepared/validated，不标 running research。

最小路线是：保全旧状态并仅停止旧未来派发 → 新的 Sol native 阶段 gate/profile 与共同数学 wrapper → 一个原生研究负责人实际分出理论/应用两队 → 逐级回读真实任务/线程/turn/记忆/消息/产物 → 以首完整终态确认启动。所有旧结果与旧证据保留，封存零推理副本保持永久不可发送。
