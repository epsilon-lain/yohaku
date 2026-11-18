# ACC 下一轮任务

本轮建议继续做 Andrews–Curtis Challenge 的 Discovery Track。先将 01635 的两条本地已验最短证书纳入候选清单，再扩大正式题覆盖。Proof Track 可以接收部分结果。固定条件下的自由词定理可作为独立审阅材料。官方截止为 2026 年 11 月 30 日 23:59 AoE，即北京时间 12 月 1 日 19:59。[Discovery 规则](https://competition.sair.foundation/competitions/acc/discovery) · [Proof Track 规则](https://github.com/SAIRcompetition/Andrews-Curtis/blob/main/competition/rules/proof.md)

## 正式题结果与优先顺序

| 优先级 | 对象 | 本地结果与后续动作 |
|---|---|---|
| 1 | ac-01635、sac-01635 | 最短步数分别为 8、10，候选文件两行均通过固定官方 CLI。工作量分别为 71、72。合并候选时按题号保留各自最短的合法证书。 |
| 2 | sac-07445 | 已证明无加元路线最少 15 步，原证书 work 128。下一次只查恰好一次加元、至多 14 步的分支。 |
| 3 | ac-04359、ac-08327、ac-09594 | 初始总词长均为 11。完整半径 5+6 的普通 AC 搜索排除 11 步以内。扩范围前先复用已建目标球，并用其它正式题检查覆盖率。 |

筛查固定 manifest 中去掉此前主要跟踪的 07445 和 08491 后，所有初始词长不超过 14 的 25 道计分题。固定普通 AC 目标球含 40,779 个状态。精确正反球半径分别为 4、5，枚举交点中的最短拼接，故 ac-01635 的 8 步解达到下界。

对 sac-01635 单独用独立解释器构球，并逐动作与固定官方实现核对。原始秩为 2，若增加生成元 $z$ 次，就需要删除 $z+2$ 次。九步内最多增加三次，沿途秩不超过 5。限定秩不超过 5 的完整正向半径 4 球有 31,501 个状态，反向半径 5 球有 6,081 个状态，交集为空。故九步内无解，十步证书达到下界。成绩规则按同题最短有效提交计分，名次和得分取决于平台上的其他提交。[筛查记录](discovery-checks.json) · [Stable AC 最短性核验](stable-checks.json) · [候选证书](submission-candidates.txt) · [CLI 回执](cli-verdict.json)

对 sac-07445，禁用加元后，第一次删元会留下一个秩一词。若这条路线能到空，该词必须是剩余生成元或其逆。将必要的取逆移到第一次删除前，就能把路线折算为到 $(x,y)$ 或 $(y,x)$ 的普通 AC 路线，再付两次删除。之前到标准有序目标的距离已证为 13。这轮把争议的换序目标查到深度 12，将指数和与有限域矩阵像用于筛选必要条件，最终用完整有序词比较中点，排除了全部 12 步以内路线。故禁用加元时 15 步恰好最短，若要做到 14 步或更短，必须真的加元。[标准有序目标证据](https://github.com/epsilon-lain/yohaku/blob/c0a6aad35ffcc7cbd8b163580f808c277ce239c6/research/theory-application-sol-2026-11-16/application/distance_certificate_guarded.json) · [换序核验程序](verify_07445_no_stabilization.py) · [换序核验结果](07445-replay.json) · [三题深至 11 的记录](discovery-next-checks.json)

## 给 Codex 的执行指令

- 理论、实践两个方向都用 GPT-6.2-Sol，负责人默认 Max，常规复核用 High，证明卡点或结果不一致可升 Ultra。原生派发时以任务回执核对实际配置。云端本轮已经按 Max 派发两组，完成理论推导和实践审查。[模型交接](https://github.com/epsilon-lain/yohaku/blob/c0a6aad35ffcc7cbd8b163580f808c277ce239c6/research/operation-family-sol62-2026-11-18/README.zh.md)
- 实践组先重放 01635 两条候选。07445 的新分支固定用恰好一次加元、至多 14 步，最高秩 3，必须有三次删除及至多十次保秩动作。枚举合法加删顺序，以原始标签和真实重编号计算。命中即用官方内核验完整路径并记录 work 与峰值。若计算触及预算，报告实际完成的层。只在完整覆盖且空交时排除该分支。
- 理论组接续任意固定供体定理。把允许变更其它槽、供体改写或借用其它关系词的影响逐项参数化，优先给出局部下界失效的最小反例。实践组以原语搜索验证条件。把可识别、展开后仍有净收益的局部变换当作候选规则，仅在已经证明下界所覆盖的动作类内用于剪枝。[理论结果与核验](https://github.com/epsilon-lain/lain-s-note/blob/2587ead4d5697e84f230bffa344e307ece7f0350/research/fixed-donor-deletion-2026-11-18/theory.zh.md)

## 复现

在固定官方 checkout 上先运行 `python3 -B discovery_pilot.py --official-root /path/to/Andrews-Curtis --submission /tmp/acc-candidates.txt`。Stable AC 的最短性核验运行 `python3 -B stable_audit.py --official-root /path/to/Andrews-Curtis --audit-script /path/to/independent_stable_verifier.py`。复用的审计器及同目录源文件锁来自固定的 Yohaku 版本。[官方固定源](https://github.com/SAIRcompetition/Andrews-Curtis/tree/a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e) · [审计器与源文件锁](https://github.com/epsilon-lain/yohaku/tree/c0a6aad35ffcc7cbd8b163580f808c277ce239c6/research/native-round2-external-review-2026-11-17/stable)
