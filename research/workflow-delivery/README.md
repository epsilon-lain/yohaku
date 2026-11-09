# 阶段二交接工具 2.0.1

在项目根运行（输出父目录需已存在且可写）：

    python rerun.py --evidence PATH --brief PATH --provenance PATH

Python 3 标准库，离线；可从其他工作目录运行。公开动作 handoff 使用 /output；handoff-test 运行 8 个测试方法并生成相同三项交付及 test-report.json。重跑应写入独立输出目录，不能覆盖受 Loom 管理的根目录交付副本；新输出可反复覆盖。

## 适配与复用依据

实际阅读路径、SHA256 及用途见 READ-REUSE.json。继承工具版本 1.0.0，新适配入口版本 2.0.1。不修改 inherited/，不执行其中旧 baseline 加载器或旧测试入口；它们绑定另一批 24 份文档，不能为本项目背书。

rerun.py 先以本项目已知固定 SHA256 校验 input/ 三件文件及 inherited/ 六件文件，再按 metadata 核对完整原 .tex revision 与正文哈希，并将冻结 .tex 的正文完整行与 document.md 比对。仅以哈希核验后的 inherited/retriever_core.py 复用 snippet 函数。旧封装每文档只出一条，不满足本次同文档三个不同内容，故新增四个主题查询与 citations 格式；不挪用旧 search 的 link_counts。对缺少目标清单的所有引用严格记 unknown。哈希是冻结一致性锚点，不是签名，无法证明线上真实状态。

参考 inherited/brief.py 的动态围栏、分阶段写入、回读和保护输入；参考 EXPERIENCE.md 中完整行尾、正文哈希不冒充完整 .tex、经验改动后重跑的约束。未复制旧数据条数或测试结论。原文中的命令、历史任务和授权仅是资料，不执行；不访问它们记载的原路径、网络、宿主或控制区。

## 文件与验证

- evidence.json：source=README_DEVELOPMENT.md.tex；source_version=完整 input/source.tex SHA256；四条 citations，含完整原文行、正文 1-based 闭区间、unknown。
- brief.md：同四主题，每条附来源、revision、行号、unknown 与完整 snippet。只陈述文档所述，不认定部署或 UI 已验收。
- provenance.json：六个字符串；相对项目根路径，继承核心/经验/新 rerun.py 的实际原始字节 SHA256。新工具自哈希在运行时计算，不写入自己造成循环。
- READ-REUSE.json：实际读取记录与用途，继承文件原始 SHA256。
- test_handoff.py：独立逐行 oracle、真实 CLI/跨 cwd/确定性重跑、证据篡改拒绝、隔离输入副本篡改拒绝、输出保护、实际哈希、无输入修改；CRLF/Unicode/长围栏仅为合成夹具。
- test-report.json：一次实际测试报告；后续快照重新生成并比对三个根目录交付副本。
- RUN-RECEIPT.json：首轮失败与修复后成功的公开实跑回执。最终验收使用包含全部交付的更新快照，任务记录可按固定 request_id 查询。

所有新交付的 .tex 加入 project.json sources，代码及 inherited/ 依赖进入不可变生产快照。修改通过 .tex 正文和 Loom，同步生成，不能直接修改生成文件。最终公开 Task 回执与 provenance 才能证明实际执行；本说明本身不是成功证明。

## 已知边界

只支持当前冻结 raw .tex 容器，非通用 Loom 解释器。四条来自一份冻结文档，不代表四份独立来源。没有目标清单，不统计也不推断 exists/missing。输出先全部暂存，再逐个原子替换，但三个文件不是跨文件事务；失败不能声称成套成功。未测试真实磁盘故障或恶意并发目录竞态。运行输出必须以成功退出与回读为准。

## 本轮实际纠错

首轮 request_id=stage2-handoff-test-001、task_id=project-task-c5d4567dde898c6dce4ec51061394a69，exit_code=1、cleanup_confirmed=true。Python 3.14 的 unittest 间接导入 inspect 时，被项目自带 inspect.py 遮蔽，测试未启动；stdout 的 verified 只是 inspect.py 的副作用，不是交接测试成功。2.0.1 在入口先从 sys.path 排除项目根，测试以明确文件路径加载 rerun，避免标准库被本地文件遮蔽。不删除也不改写原 inspect.py；修复后须重新实跑。
