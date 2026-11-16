# Stable sac-08491：外部补充审阅

审阅日期：2026-11-17。本次是公开冻结材料后的**新外部独立复核**，不是原生 round2 的补交任务，也不改变原 native root 的 error／1800 秒 interrupted、独立核验未完成记录。未启动 host 或模型实验，未运行上传的研究代码，未上传比赛平台；本报告随后作为外部审阅材料单独公开。

固定官方仓库为 `SAIRcompetition/Andrews-Curtis`，commit `a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e`。先逐项核对 30 份官方文件的 SHA256 与 Git blob，再执行官方校验器。对象为 `sac-08491`，起点为 `((-2,-1),(-2,-2,-1,-1,2,2,1))`，目标为空 presentation；实例 SHA256 为 `757bc38cade1df7592589a7d7b45edbf4f793cbe05b09e538651aa28c9b8498c`。

全局覆盖理由成立：起始 rank 为 2、终态为 0；若加元 z 次，删元必为 z+2 次，因此步数 n≥2z+2。n≤9 时 z≤3，整条路线的 rank≤5。只需完整枚举 rank≤5 诱导有向图，就能排除官方允许 rank≤8 的全部九步内路线。

新 verifier 独立构建动作表与自由约化，每个正向展开状态尝试全部 257 个 ID，并逐次同官方语义对照。逆向保 rank 边用固定逆动作；逆 destabilize 独立枚举全部新生成元标签 g∈{1,…,k+1}、全部 relator 插入位置 i∈{0,…,k}，以省去 g 的保序嵌入提升原标签，再插入正单字 (g,)。任何合法删元前驱必属于这一枚举。逆 stabilize 仅在末项为 (k,) 且其余 relator 不含 ±k 时存在，前驱唯一。各逆候选均正向重放验证。全部状态按精确有序字组去重；无重标号、共轭、循环或同构取商，无长度或累计 work 剪枝。

| 完整球 | 各层新状态数 | 总状态数 |
|---|---|---:|
| 起点正向 B4 | 1,14,160,1910,26426 | 28511 |
| 空目标逆向 B5 | 1,1,3,26,340,5710 | 6081 |

两球空交；任意九步内路线在第 4 步切分（不足四步取终点）都会产生交点，故距离≥10。冻结旧路线 `(7,4,12,1,12,2,5,5,16,15)` 经官方重放合法，长 10、峰值总长 9、含初态累计 work 为 50，因而**该固定实例全局距离恰为 10**。这仅证明固定实例，不是一般 AC／Stable AC 猜想的无穷族证明，也不是比赛平台成绩或宏方法收益。

原 ZIP 中球产物通过 SHA256 核验。新球逐状态、逐最短层数与作者的 34592 项记录完全一致，所有作者路径亦由独立语义及官方语义重放通过；新球文件甚至与原产物字节相同，SHA256 为 `bc18a78605cf2a979179c096f32616e580b2f2483b1035f99795816d2cd722fb`。最终复核含 783992 次逐项 apply 对照，无 guard 触发。作者旧尾注“rank cap3”与执行 cap5 不符，已显式勘误；本次实算确认 cap5，未发现影响最短性结论的缺口。

复现时将本目录的脚本和 `official-source-lock.json` 放在一起，在固定官方 checkout 上执行：

```bash
python independent_stable_verifier.py --official-checkout /path/to/Andrews-Curtis
python independent_stable_verifier.py --official-checkout /path/to/Andrews-Curtis --original-balls /path/to/r2cap5-balls.json
```

脚本只依赖 Python 标准库，输出完整新球及 JSON；原球参数可选。原始输入的固定 URL、包哈希及作者材料位置见 `review-provenance.json`。公开复核只需脚本、锁文件、compact JSON 和本文，无须重复发布球文件。
