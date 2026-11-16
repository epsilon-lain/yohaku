# 下一轮原生实验：概念组合能否帮助找到真正更短的比赛路径

目标是找到至少一条经过官方本地验证、**完全展开后的原始操作数严格少于固定旧路径**的解，并检验概念压缩是否帮助搜索。宏名称的数量、描述字符数或work下降都不能替代这个指标。

本目录是给用户本机 Yohaku 的具体执行任务与离线验收工具。**尚未在原宿主启动本轮研究，也没有在这里发现新的更短比赛解。** 工程准备不计作原生研究、AI自主续行或组织分化。现有的理论、计算、失败和原生回执全部保留。

## 任务入口

把 [CODEX_TASK.md](CODEX_TASK.md) 交给运行在本机 Yohaku 项目目录的 Codex 执行；具体方法和对照边界见 [PROTOCOL.md](PROTOCOL.md)。执行者先核查旧总负责人、在途任务、阶段期限与真实剩余额度，再把新用户目标交给原生负责人。不能只因旧快照显示running就重发，也不能把本准备包当成已经派发成功。

## 已锁定的比较基线

| 题目 | 旧路径原始步数 | 可否继续以缩短为目标 |
|---|---:|---|
| ac-08491 | 8 | 固定普通AC动作表下已证明最短；作为验收负例 |
| ac-07445 | 13 | 固定普通AC动作表下已证明最短；作为验收负例 |
| sac-08491 | 10 | 目前只有合法上界，尚未证明最短 |
| sac-07445 | 15 | 目前只有合法上界，尚未证明最短 |

[baselines.json](baselines.json) 保留完整动作、来源提交和SHA。这里比较的是**我们已归档的路径**，不代表实时排行榜或他人最佳结果。普通AC和Stable AC的动作、终点不同，最短性证明不能跨题目规格搬用。两支原生方向也可以自主选择其他尚未证明最短的正式题，但必须先登记、验证并冻结基线和评估版本。

当前验收器只接受上述四条锁定基线；新题需要在看到候选结果前，独立登记并审定新版基线和对应验收器，保留本版。候选输入无权覆盖、填长或替换比较基线。

## 验收工具

准备固定官方版本 `SAIRcompetition/Andrews-Curtis@a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e` 的checkout。输入格式为：

```json
{
  "challenge_id": "sac-08491",
  "tokens": ["named_combination", 16, 15],
  "macros": {"named_combination": [7, 4, 12, 1, 12, 2, 5, 5]}
}
```

这个例子仍然展开成10步，是接口示例，没有改进。工具逐层展开宏并调用固定官方验证器，同时验证旧路径；只有合法且原始步数严格更短才通过。已证最短题若出现矛盾，转人工复核，不能直接宣布突破。循环宏、未定义宏、非法动作和超限输入均拒绝。

```sh
python3 -B validate_candidate.py examples/same-path-one-macro.json \
  --official-checkout /path/to/Andrews-Curtis --output candidate-verdict.json
```

这个负例把完整8步路径装进一个宏；输出应明确仍为8步，没有严格改善。[官方来源指纹](official-source-provenance.json) 用于核对本地官方代码。验收结果不等于平台上传、榜单领先或文献首创。

[PREFLIGHT.json](PREFLIGHT.json) 保存该负例的实际验收回执；[VALIDATION.json](VALIDATION.json) 记录工程验证范围。22项单元检查通过，覆盖真实基线重放、宏循环、错误终点、Stable动作前提和伪造比较基线。测试中的人工正面fixture不属于比赛成果。

```sh
YOHAKU_OFFICIAL_CHECKOUT=/path/to/Andrews-Curtis \
  python3 -B -m unittest discover -s . -p test_validate_candidate.py -v
```

宏字典、训练／测试划分、原始操作评估次数、搜索与建字典成本必须留证。共享数学库继续开放；对照程序和状态需冻结。若两臂都由已读过宏的同一模型指导，必须承认污染，不能据此作宏方法的因果优势结论。
