# sac-07445 最短步数 15

Codex 实验组于 2026 年 11 月 18 日完成此题的全分支计算机辅助证明。搜索和独立核验各由一名云端 GPT-6.2-Sol / Max 协作者执行。既有 15 步证书再次通过固定官方 CLI，work 为 128，峰值总关系词长为 13。全部 14 步以内的路线均已排除，因此最短步数恰为 15。这次计算给出步数下界。15 步证书里是否还有更低的 work 仍待研究。候选文件保存在仓库，本轮未向比赛平台提交。[官方 CLI 回执](cli-verdict.json) · [候选文件](submission-candidates.txt)

## 为什么七个分支足够

设一条从秩二到秩零的路线加元 $a$ 次。它必须删元 $a+2$ 次，所以加删合计 $2a+2$ 步。假定总步数至多 14，那么 $0\le a\le 6$，保秩动作至多 $12-2a$ 步。以下是在固定动作表中把每条这种路线送到较小搜索图的过程。[比赛固定源](https://github.com/SAIRcompetition/Andrews-Curtis/tree/a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e)

1. 一开始预置 $a$ 个独立的正单字母关系词，固定秩为 $2+a$，至多为 8。分别维护当前生成元编号和当前关系词槽位向预置编号、槽位的保序嵌入。原路线的加元激活下一个预置字母及对应的末尾槽位。原路线的删元冻结被删除的正单字母词，并从两张活跃表移掉对应编号及槽位。冻结字母在其它词中没有出现。之后的保秩动作只改动活跃槽位和使用活跃字母，且新加入的词使用自己的新字母。原路线归零时，预置状态中的所有词都是相异的正单字母词。于是每个保秩动作可映射到固定秩中，得到一条从原题加上 $a$ 个单字母词到正单字母词排列的路径。
2. 再把预置的新字母都映到单位元，只保留 $x,y$。取逆、右乘另一关系词或其逆、以及共轭均与这个自由群同态相容。用新字母做的共轭投影成原地动作，可以省掉。保留 $2+a$ 个关系词槽位，包括投影出空词的槽位。投影的目标是 $x,y$ 和 $a$ 个空词。投影成功只说明这个必要条件成立。投影路线未必能提升为原路线。
3. 对投影后的关系词排序。置换槽位只会重标动作的作用槽与供体槽，因此排序后的状态保留所有路径在图中的像。逆动作同样在动作表内。若存在至多 $12-2a$ 步的投影路线，起点和终点半径各为 $6-a$ 的完整球至少共享一个状态，沿投影路线取中点即可。空交排除原路线。

## 完整覆盖

| 加元次数 | 保秩动作上限 | 每侧半径 | 起点球状态 | 目标球状态 | 交点 |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 12 | 6 | 1,165,712 | 303,510 | 0 |
| 1 | 10 | 5 | 615,294 | 185,532 | 0 |
| 2 | 8 | 4 | 54,145 | 21,548 | 0 |
| 3 | 6 | 3 | 3,742 | 1,864 | 0 |
| 4 | 4 | 2 | 270 | 170 | 0 |
| 5 | 2 | 1 | 19 | 15 | 0 |
| 6 | 0 | 0 | 1 | 1 | 0 |

完整搜索通过固定官方 Python 内核生成投影后的邻接状态。各球的大小含所有已完成层，比较键是排序后的完整关系词元组。七个分支都在状态和时间上限内完整结束，共调用内核 4,250,423 次。独立 C++ 实现也跑完了七个分支，逐层状态数一致，交点均为零。[官方内核数据](all-add-counts.json) · [独立 C++ 回执](audit/projected-cpp-audit.txt)

恰好一次加元的分支也用保留全部标签的秩三搜索、按槽位及生成元重命名取商的秩三搜索核验。两项均保留新增生成元在关系词中的全部出现。实验组也试过三种带 3,072 前沿宽度的启发式排序，均未找到短路线。最短性结论使用完整覆盖的空交。[保留标签的结果](lead/exact-results.json) · [完整词取商结果](quotient-result.json) · [启发式结果](beam-result.json)

## 复现

检出上述官方固定提交，将下面的 `official` 改为该 checkout 的绝对路径，在本目录运行。搜索脚本会核对 manifest、官方内核源文件及题目实例哈希。若中途达到资源上限，脚本退出并报告对应层。

```bash
official=/path/to/Andrews-Curtis
pycache=$(mktemp -d)
PYTHONPATH="$official/competition/tools" PYTHONPYCACHEPREFIX="$pycache" python3 -B check_multiple_additions.py \
  --manifest "$official/competition/tools/verifier/data/manifest.json" \
  --output /tmp/sac-07445-all-add-counts.json
PYTHONPATH="$official/competition/tools" python3 -B -m verifier \
  --manifest "$official/competition/tools/verifier/data/manifest.json" \
  --submission submission-candidates.txt --pretty
```

独立 C++ 核验可以在本目录直接复跑。它使用固定题目的两个初始词和冻结规则中的取逆、右乘、共轭操作。

```bash
g++ -std=c++20 -O3 -Wall -Wextra -Werror -pedantic audit/projected_rank3.cpp -o /tmp/projected_rank3
/tmp/projected_rank3 --direct-all
```

下一轮可先把已有 15 步证书纳入本地候选，并把缩步计算转给此前已经排除 11 步以内的 `ac-04359`、`ac-08327`、`ac-09594`。这项下界方法可以复用到其它以空表示为目标的 Stable AC 题，具体能证明多深取决于各投影球的覆盖规模。[上一轮题目筛查](https://github.com/epsilon-lain/yohaku/blob/50a6a86c0a33e35564a9a26736e7c59f62e2e9c3/research/acc-next-round-2026-11-18/discovery-next-checks.json)
