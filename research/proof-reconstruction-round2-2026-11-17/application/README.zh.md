# 固定已知证书的压缩对照

结论：42 个主 armcases 全部完成。21 个固定案例中，两臂各改善 7 例、共省 35 个官方原语；两臂最终动作列表逐项完全相同。加入 whole-object 宏没有获得额外收益。真实题 `sac-07445` 仍为 15 步、work 128；没有平台提交或排行榜访问。

这是**给定已知解的证明压缩**，不是从头求解，也不是原 v1 solver 的对照。数据中的训练标签 `ms-train-xxxx` 映射到官方 Stable 提交 ID `sac-train-xxxx`，并逐条核对官方训练 manifest 的 initial/target/spec。

| 固定分组 | 案例数 | 每臂原长度合计 | baseline 最终长度 | whole-object 最终长度 | 每臂完整 work 原→新 | 新增宏额外节省 |
|---|---:|---:|---:|---:|---:|---:|
| 旧 development | 4 | 59 | 49 | 49 | 350→322 | 0 |
| 新固定 public-training test | 16 | 271 | 246 | 246 | 1972→1902 | 0 |
| 固定真实题 sac-07445 | 1 | 15 | 15 | 15 | 128→128 | 0 |
| 合计 | 21 | 345 | 310 | 310 | 2450→2352 | 0 |

所有 14 次主结果的接受改写均为“一原语替换更长窗口”：每臂 7 次，每次省 5 步。改善的 7 个不同官方训练案例为 `sac-train-0379`、`0013`、`0014`、`0081`、`0235`、`0031`、`0009`（后六个同属 sac-train 前缀）。完整两臂原始/最终动作、接受窗口、精确终点、官方 verdict、资源和调用数均在 `results.json`。`improved-certificates.json` 保留两臂的 14 条证书记录；`improved-training-submission.txt` 去重为 7 条官方文本格式，未上传。真实题没有改善，因此没有生成新的真实题提交文本。

主代理在实验结束后独立检查发现，7 例都来自同一机制：窗口入口恰为有序状态 `(y,x)`，把旧六原语 `[0,2,5,2,8,16]` 替换为一个原语 `[15]`，二者都到 `(x)`，再用原后缀 `[15]` 到空。旧路径绕行“先规范到 `(x,y)`”的多余中间目标；正置换次序 `(y,x)` 本已可以直接 destabilize。这是事后解释，不是七种独立新机制，也不是 donor 宏的收益；没有据此改候选库或重跑。

两臂共用精确有序全状态匹配，包含 rank，搜索每个起点的任意后续窗口，不要求最大连续共轭块。baseline 只用精确重复状态删环与一个适用原语。whole-object 另用三步左乘、四步现成 donor 共轭，以及 h v^(±1) h^-1 的 2|h|+4 步展开，h 自由约化且 |h|≤2。所有宏的原语逐步调用官方 apply；不是免费宏。

每轮先按完整新路径的 length、work、peak、start/end、完整动作列表选最优，再完整官方 verify，严格减少原语长度才能接受。最多接受三次，接受后从新证书重建状态索引。本次所有搜索轮都穷尽了配置候选库，没有触及调用或时间上限；因此不存在截断搜索导致的排序不完整。此有限样本上的零增益不意味着宏恒等式无效，也不外推为其他已知证书或从头求解任务的结论。

| 费用项目 | baseline | whole-object |
|---|---:|---:|
| 主结果 armcases | 21 | 21 |
| 主结果 search 官方 apply | 102712 | 214176 |
| 主结果 verify 内部官方 apply | 736 | 736 |
| cap 命中 | 0 | 0 |
| 非预期 verify 失败 | 0 | 0 |

每臂每例同为 50000 search apply、15 秒、最多三次接受的**上限**，实际耗用不同。whole-object 多执行 111464 次主 search apply；本结果不将墙钟时间作为因果速度论据。每条路径的官方 work 包含初始态一次，peak 包含所有展开中间态。

审读前 revision 1 做过一次诊断及一次 development，修正实现后 revision 2 各重跑一次；旧尝试未隐去。累计费用如下，均包含开发重试：

| 账目 | 官方 apply 次数 |
|---|---:|
| 两次诊断 search | 25434 |
| 两次 development search（含固定真实题） | 143084 |
| 一次新 test search | 245346 |
| **全部 search** | **413864 / 2100000** |
| 两次诊断 verify 内部 apply | 7814 |
| 两次 development verify 内部 apply | 652 |
| 一次新 test verify 内部 apply | 1146 |
| **应用全部 verification** | **9612 / 25000** |

理论 2000、主代理独立复核 3000 另预留，总 verification 上限 30000；它们的实耗由各自产物及根报告合并。`attempt-ledger.json` 记录所有版本尝试和实际调用；同案例预算始终以原始 training source ID 累计，ms→sac 提交标签修正没有重置预算。预期资源反例中出现的 `E_LENGTH_LIMIT` 属于合成回归，不是遗漏的实验异常。

后续独立验收由主代理完成：21 例的原始及两臂最终证书共 63 条路径，独立动作解释器与官方结果一致；官方完整文件锁 CLI 接受 7 条训练改善证书及旧真实题证书。主代理报告官方 apply 共 2026（1930 路径复核、96 CLI），理论另报 1716；与应用 9612 合计 13354/30000。独立解释器自有 965 次动作不冒称官方 apply。这些后续核验计入根报告，不改应用被冻结的搜索结果或 ledger。

冻结顺序：`FREEZE.json` 于 2026-11-17 11:09:21.970800 UTC 写入；`TEST-ACCESS.json` 于 11:09:25.315285 UTC 记录首个新 test 动作数组访问。冻结脚本 SHA256 为 `27deee0cbf455525abdeb7b7e513e54f2a148ebc5667f38c5b0383826c2a5500`，配置 SHA256 为 `45cd5ff906096591416665ca968e0306f3fb6585a2b7a6b46e79ccba7991fa2f`，执行后均保持不变。16 个 ID 从长度≤20 的剩余公共训练记录，按 SHA256(官方 commit|training_id|固定 salt) 升序取前 16；旧 4 development 和旧 4 evaluation 均排除。冻结前只读取选择用 ID/声明长度，没有索引这些新 test 的动作数组。没有因零命中增加样本或调参。

`selfcheck.json` 记录 512 个 rank 2/3 全 h、全有序 donor/target、两符号编译回归，均通过；另有 synthetic 12→4 回归（baseline 12、whole-object 4）及中间态资源限制反例。`PROVENANCE.json` 记录固定源 Git blobs、SHA256、实际加载和单层 API 计数方法；直接 compile 已核源码，不读取缓存 pyc。信息流、主代理审读修正与明确协作来源见 `METHOD-LOG.md`，首版证据见 `raw-v1/` 与 `REVISION-1-PRESERVED.json`。

标准库复现（Python 3.12；保持来源和 `../PROTOCOL.json` 相同）：对一个新的输出目录，依次执行以下子命令。正式发布目录已有 freeze 与 test-access，脚本会拒绝静默覆盖或重复执行。

```bash
python -B run_experiment.py selfcheck --source-root /path/to/ac_official --output /tmp/reconstruction-replay
python -B run_experiment.py development --source-root /path/to/ac_official --output /tmp/reconstruction-replay
python -B run_experiment.py freeze --source-root /path/to/ac_official --output /tmp/reconstruction-replay
python -B run_experiment.py test --source-root /path/to/ac_official --output /tmp/reconstruction-replay
python -B run_experiment.py report --source-root /path/to/ac_official --output /tmp/reconstruction-replay
python -B export_training_submission.py /tmp/reconstruction-replay
```

干净复现只运行修正版一次，所以不应得到历史开发重试的累计费用；主 42 armcases 的路径、资源、枚举结果和选择 ID 应一致。旧版尝试可从 `raw-v1/` 独立重算。没有调用本机 Yohaku、外部 solver 或网络 API；本目录交由主代理审核发布 GitHub。
