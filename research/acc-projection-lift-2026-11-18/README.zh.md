# Stable AC 投影搜索和路线还原

Codex 实验组在固定比赛规则下比较了完整秩三搜索和投影搜索。两道跟进题得到已由官方 CLI 和独立解释器共同接受的证书。`sac-04359` 的最短步数在 **17–19** 之间，`sac-08327` 在 **17–20** 之间。19 步、20 步路线均由投影引导搜索找到并还原。本轮证书仅经过本地验证。[候选路线](submission-candidates.txt) · [官方回执](cli-candidate-verdict.json) · [独立回放](independent/candidate-replay.json)

## 同预算对照

固定恰好一次加元，把加元和删元移到路线两端。对照臂保留新增生成元，投影臂令该生成元等于单位元并保留第三个关系词槽位。两臂用同一个 C++ 搜索器，分别取各自的关系词槽位和无符号生成元重命名轨道。固定字母的投影关系用于原始有序词，重命名取商用于各臂内部搜索。每臂完整构造正向半径 4、反向半径 5 的球。球没有共同状态时，再检查正向半径 5 外层能否接上反向球，从而完整覆盖至多 10 个保秩动作。

预先选定此前未筛过的六道正式题。按初始总词长 15、16、17 分层，在各层将 `SHA-256("yohaku-acc-projection-v1:" + 题号)` 排序后取前两题。另加此前筛过的两道短题作为跟进，以及已有证书的 `sac-01635` 作为阳性对照。[运行数据](results-rss.json)

| 样本 | 题目 | 直接搜索 | 投影搜索 |
| --- | --- | --- | --- |
| 六道首次筛查 | 04416、07667、00066、00626、09241、04551 | 保秩距离 ≥11 | 保秩距离 ≥11 |
| 两道跟进 | 04359、08327 | 保秩距离 ≥11 | 保秩距离 ≥11 |
| 阳性对照 | 01635 | 保秩距离恰为 8 | 保秩距离恰为 8，且找到等长的合法还原 |

八道研究题逐题计算耗时比例，中位数为 **11.5 倍**。从准备输入到搜索子进程返回的耗时中位数由约 **4.64 秒**降到 **0.40 秒**。搜索子进程峰值常驻内存中位数由 **129.2 MiB** 降到 **35.0 MiB**，用 Linux 的 `VmHWM` 读取。两个搜索臂分别在新进程冷启动，交替运行次序，共用相同的状态、内存和时间上限。主对照的八道题都是空交，耗时包含投影预处理。阳性对照另测还原约 0.001 秒。后续启发式搜索的还原时间单独计入。

在两道跟进题上，将上限提高到 12 个保秩动作。直接臂在构造反向第 6 层时触及每球 180 万状态上限。投影臂在相同预算下完整结束，两道题均排除一次加元的所有 16 步以内路线。每题投影耗时约 10 秒。[深一层对照](deeper-followups.json)

## 从投影路线得到证书

对 04359 和 08327，采用宽度 4096 的启发式前沿和共享反向半径 5 球扩大搜索。共享球构造约 0.91 秒，每题前向搜索约 3.21 秒，还原约 0.002–0.003 秒。还原逐层用官方秩三动作枚举所有能接到下一投影状态的实际状态。两条选中的投影路线每层都只留下一个实际状态，最后到达三个可删的正生成元。

| 正式题 | 投影保秩动作 | 还原后含一次加元 | 去掉独立的新增元 |
| --- | ---: | ---: | ---: |
| `sac-04359` | 17 | 21 步，work 224 | 19 步，work 193 |
| `sac-08327` | 18 | 22 步，work 220 | 20 步，work 188 |

两条路线的新增元始终保持独立，移去它的加入和删除仍为合法证书。本次展示的收益是用投影降低搜索成本、获得可验证候选。启发式找到的长度提供上界。[启发式数据](guided-results.json) · [独立还原轨迹](independent/projection-lifted-replay.json) · [含加元的官方回执](cli-lifted-verdict.json)

另一条秩二启发式路线达到 `sac-08327` 的 20 步、work 187。相同的实验还给出了 `sac-09594` 的 19 步、work 182 路线。09594 是额外跟进题，耗时统计和下界证明均限于上面的对应样本。[额外路线](lift_audit/discovery-candidates.txt) · [额外路线官方回执](lift_audit/discovery-cli-verdict.json)

两题的 17 步总下界覆盖所有加元次数。零次加元的图完整排除了至多 14 个保秩动作，加上两次删元共覆盖至多 16 步。一次加元的图通过投影排除至多 12 个保秩动作，加删元共四步。两至六次加元由独立脚本对所有剩余预算的正反球求交，全部为空。七次加元需要九次删元，若总长至多 16 则没有保秩动作，两条初始非单字母词会一直保留。更多加元的加删本身至少要 18 步。[零次加元记录](rank-two-deeper.json) · [多次加元记录](independent/multiple-additions-through-16.json)

## 投影无法保证的还原

在 04359 的一段合法前缀中插入一次用新增元做的共轭，投影状态保持原样，但真实的关系词里留下了新增元。投影中间状态距目标只剩一步。逐一检查 33 个真实保秩动作后，唯一能在一步内进入目标投影的动作会留下不能直接删完的真实状态。先撤销这个共轭，再完成最后一个可见动作，就能顺利删元。因此从该中间状态到可删目标，投影恰需一步，真实恰需两个保秩动作。只记录新增字母的指数和也会丢失这次共轭。[构造和回放](lift_audit/fibre-witnesses.json)

## 复现

需要 Linux、C++20、Python 3 和固定比赛源码。先将 `official` 设为该提交的 checkout 绝对路径，再从本目录运行。对照脚本核对 manifest 和官方内核的指纹。[官方固定源码](https://github.com/SAIRcompetition/Andrews-Curtis/tree/a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e)

```bash
official=/path/to/Andrews-Curtis
manifest="$official/competition/tools/verifier/data/manifest.json"
export PYTHONPATH="$official/competition/tools"
export PYTHONPYCACHEPREFIX="$(mktemp -d)"
g++ -std=c++20 -O3 -Wall -Wextra -Werror -pedantic search.cpp -o /tmp/acc-projection-search
python3 -B benchmark.py --binary /tmp/acc-projection-search --manifest "$manifest" --output /tmp/acc-benchmark.json --flip-order
python3 -B benchmark.py --binary /tmp/acc-projection-search --manifest "$manifest" --output /tmp/acc-deeper.json --forward-radius 5 --reverse-radius 6 --only sac-04359 --only sac-08327
python3 -B guided_projection.py --manifest "$manifest" --output /tmp/acc-guided.json
python3 -B rank_two_followup.py --binary /tmp/acc-projection-search --manifest "$manifest" --output /tmp/acc-no-add.json --reverse-radius 7
python3 -B independent/check_multiple_additions.py --manifest "$manifest" --output /tmp/acc-multi-add.json --total-limit 16
python3 -B lift_audit/contamination_witness.py --manifest "$manifest" --output /tmp/acc-lift-witness.json --ids 04359
python3 -B -m verifier --manifest "$manifest" --submission submission-candidates.txt --pretty
```
