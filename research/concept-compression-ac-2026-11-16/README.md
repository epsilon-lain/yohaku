# 概念压缩怎样连接合法变换：Andrews–Curtis 首轮试验

日期：2026-11-16。状态：**完成本地有界对照、取得正式题解并通过官方验证器；对固定 AC 题 `ac-08491` 另行认证其全局最短长度为 8；尚未上传平台**。本轮没有解决 Andrews–Curtis 猜想，没有比较排行榜，不声称取得平台新纪录或数学新颖性。

**English abstract.** We test a concrete interface from reusable concepts to legal Andrews–Curtis transformations. A fixed macro library expands into the official primitive moves, and every internal transition counts toward the same search budget. Two heuristic search arms share an exhaustive radius-four target ball. Both solve all eight selected training cases and two of eight selected scored AC cases; macro search returns the same solution lengths and uses more primitive evaluations in aggregate. Four AC/Stable AC submission lines pass the pinned official verifier. A separate unpruned meet-in-the-middle certificate establishes distance eight for the fixed AC instance ac-08491. This is a bounded negative/neutral pilot and finite optimality check, not autonomous concept learning, a leaderboard record, or a proof of the conjecture.

## 问题与数学接口

用户的研究设想是：用可复用的概念及组合规则更简洁地描述或处理同一对象。数学形式化与向量精确例子见[独立数学笔记](https://github.com/epsilon-lain/lain-s-note/tree/main/research/concept-compression-2026-11-16)。本目录只测试其中一个接口：**把高阶操作写成合法原始操作的可执行展开**。

比赛的 AC 状态是两个有序关系词；终点必须精确为 `((1,), (2,))`。本轮使用官方 14 个原始 move，不把交换次序或同构后的终点当作完成。Stable AC 解由已核验的 AC 解追加 `[16,15]` 得到，并另行完整验证。

如果一个宏展开为三步，它的解长度贡献就是三步。宏的中间状态也受到长度限制，最终完整路径的累计工作量由官方验证器逐步核对。宏名称、文字篇幅或搜索中的一条队列边，不是比赛计分的原始步数。固定宏库仍包含每个原始一步动作，因此宏只是可用路径的另一种表示；任何最优性结论还需要正确的加权搜索或另行证明。本轮搜索是启发式的，**它本身不提供最优性保证**；后文只对 `ac-08491` 用独立完整枚举认证。

这也与[较早的免疫式／自主组织案例](../immune-autonomous-2026-11-16/README.md)分开：本轮由当前 AI 协作团队编写、复核并运行，未把这些动作倒填到原 Yohaku 运行中的两组。

## 固定实验条件

上游固定为 [`SAIRcompetition/Andrews-Curtis@a0fd6e6`](https://github.com/SAIRcompetition/Andrews-Curtis/tree/a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e)。规则及动作表分别见该版本的 [Discovery 规则](https://github.com/SAIRcompetition/Andrews-Curtis/blob/a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e/competition/rules/discovery.md)和[验证器文档](https://github.com/SAIRcompetition/Andrews-Curtis/blob/a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e/competition/tools/verifier/README.md)。源码和数据不随本目录重复分发；[upstream-lock.json](upstream-lock.json)记录所需 18 个文件的 SHA-256 与 Git blob。

| 条件 | primitive 臂 | macro 臂 |
|---|---|---|
| 案例 | 训练 AC ID 排序前 8；正式 AC 按初始总词长、ID 排序前 8 | 相同 |
| 每例预算 | 最多 20,000 次实际原始 move 计算 | 相同，宏内部每步也计数 |
| 搜索长度截断 | 超过总词长 32 的搜索候选或宏中间状态立即丢弃，该步计算仍计数 | 相同 |
| 队列优先级 | 当前约化总词长、已走原始步数、插入次序 | 相同 |
| 目标附近知识 | 完整半径 4 的反向 BFS 球 | 同一只读球 |
| 动作 | 14 个原始动作 | 先尝试预设宏，再尝试全部原始动作 |

案例规则在首次搜索前确定，没有用已知训练解选择宏或引导搜索。正式样本偏向短输入，不能代表全部 10,115 个 AC 题；这里的“训练集”是主办方给定的数据名称，没有训练模型参数。

共享目标球是**无长度剪枝**的完整 BFS：各层新增状态数为 `1,10,77,574,4453`，共 **5115** 个状态，构建需 **9268** 次原始 move 计算，最大总词长 17。每次计算都与官方 `core.apply_move` 对照一致，这项独立核验另有 **9268** 次原始动作调用。球内保存的终点后缀是全局最短后缀；这不能推出把启发式前缀与后缀相接得到的整体路径最短。预计算与验证成本单列，双方使用完全相同的球。后文每臂计数只衡量搜索，另行的官方路径回放和工具链检查不包含在其中。

宏库由本轮研究者预先编写，**未实现从数据自动发现或学习新概念**：

- 循环外壳约去：若关系词首尾互逆，按真实生成元共轭逐层约去；连续至少两层时合为一个宏入口。
- 左乘另一关系词或其逆：通过“取逆—右乘—取逆”展开为三步。例如对第一个关系词左乘第二个，展开为 `[0,3,0]`。

代码统计所有宏中间 move，包括随后被丢弃、重复或因截断停止的计算。词长检查、队列操作和宏模式检测的 CPU 成本不包含在 move 计数中；结果另列单次运行时间，但不把这种计数叫作完整运行成本或模型 token 成本。

## 实际结果

| 样本 | primitive 解出 | macro 解出 | primitive 计算次数 | macro 计算次数 |
|---|---:|---:|---:|---:|
| 训练 8 例 | 8/8 | 8/8 | 560 | 714 |
| 正式 8 例 | 2/8 | 2/8 | 124563 | 124814 |

两臂在所有解出的案例上返回**相同的展开后长度**。宏臂只在训练第 7 例减少了原始动作计算，在其他训练例增加或持平；正式成功例也增加。两臂总计分别为 125123 和 125528 次，宏臂多 405 次。**本轮不支持这套宏库带来总体改进。**单例的减少也不能证明稳定优势。

正式失败案例 `ac-04359`、`ac-08327`、`ac-09594`、`ac-00104`、`ac-00399`、`ac-00974` 全部保留；两臂在每例都耗尽 20,000 次预算。它们不是已证无解，不能由有界失败推断数学障碍。

| 可提交的正式 ID | 原始步数 | 官方工作量 | 本地官方结果 |
|---|---:|---:|---|
| `ac-08491` | 8 | 49 | `ok: true` |
| `sac-08491` | 10 | 50 | `ok: true` |
| `ac-07445` | 17 | 157 | `ok: true` |
| `sac-07445` | 19 | 158 | `ok: true` |

完整文件是 [submission.txt](submission.txt)，完整官方 CLI 回执是 [official_verdict.json](official_verdict.json)。每个臂的每个成功 AC 解也单独调用官方 `core.verify`，回执与路径保存在 [results.json](results.json)，避免重复 ID 的“首个成功后跳过”规则漏检另一臂。最终提交文件每个 ID 只出现一次；选择展开长度较小的解，同长时以臂名的字典序作固定决胜规则。

平台评分取决于其他队伍提交的最短已验证解。这四行目前只有本地通过证据；没有在线提交回执、排名或得分，不称为获奖或领先。Stable AC 的两行也不是两项独立数学发现。

## 单题的严格最短长度证书

对 `ac-08491` 另行构建从初始有序状态出发的**完整半径 3 球**：每层新增 `1,13,129,1186` 个状态，共 1329 个，需 2002 次原始动作计算。这里不商去交换、符号或同构，不做词长剪枝；每条计算出的边都与官方动作实现交叉核对。它与上述完整目标半径 4 球的交集为空。

14 个原始动作都有对应逆动作。若存在长度不超过 7 的路径，走至距起点不超过 3 步的位置后，距终点最多还需 4 步；该位置必在这两个球的交集中。空交集因此排除了全部 0 至 7 步路径。官方已经验证的 8 步路径给出上界，两者合起来认证：**此固定 AC 题的全局最短长度恰为 8。**这是有限题的最短性核验，不声称文献或比赛中的首次发现。

[certify_shortest.py](certify_shortest.py) 是独立复现入口，[shortest_certificate.json](shortest_certificate.json)包含正式实例身份、完整球层数、状态集合哈希、空交集及 8 步官方回执。独立脚本重建两球需 `9268+2002` 次研究实现计算和相同数量的官方交叉核验调用，另有 8 步见证回放；这些费用不加到公平对照的任何一臂中。本证明不适用于 Stable AC 的 10 步路径，也不认证 `ac-07445` 的 17 步路径最短。

## 复现与来源核验

Python 3.10+，仅标准库。先把固定上游工具和数据准备到当前仓库之外，再运行：

```sh
python prepare_official.py --destination /tmp/ac-official-pinned
python pilot.py --official-root /tmp/ac-official-pinned --output /tmp/ac-pilot-rerun
python certify_shortest.py --official-root /tmp/ac-official-pinned --output /tmp/ac-shortest.json
```

准备器逐文件校验哈希，发现已存在但不同的文件会拒绝覆盖。锁定清单不含任何已知训练解的动作序列文件。`pilot.py` 在导入官方实现前重新核对锁定文件，默认重新计算共享球、32 次搜索及全部成功解的验证。搜索路径与 move 计数是确定的；`wall_seconds` 随机器负载变化，不要求输出 JSON 逐字节相同。

本次已实际通过准备器的网络下载分支，在新的目录中取得全部 18 个文件，再从该干净目录重放。除运行时间字段外，所有结果字段一致；两份提交文件和两份 CLI 回执逐字节一致，见 [reproduction_check.json](reproduction_check.json)。

本次还验证了官方工具链：63/63 个 golden vectors，训练 manifest 的 848 个 challenge 哈希，以及正式 manifest 的 20230 个 challenge 哈希全部通过；[official_toolchain_checks.json](official_toolchain_checks.json)保存摘要。这些是官方工具的复现检查，不计为原创数学成果。上游采用 Apache-2.0；本目录通过固定来源链接、哈希和准备器使用它，不把上游实现冒充本研究原创代码。

## 此轮结论与下一步

可核验结论是：概念压缩能够通过宏展开与合法变换建立一个具体接口；但“宏表达更短”本身没有在本轮产生更短的正式解，也没有降低总 move 计算。下一步应当先提出有理由的新结构或选宏规则，在独立案例上检验，再比较完整构建成本、搜索成本与展开路径长度。不能在看到这 16 例的结果后调参，再把同一批样本称作未见测试集。

本轮记录保留正反结果、预算截断和来源。它为理论提供可运行的校验对象，尚未建立“最短描述等于最短求解路径”的一般定理。
