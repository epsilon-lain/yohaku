# 共同共轭框架：可执行规则、一个旧训练命中与保留的零结果

本小队完成了两版带精确端点和原语收费的框架重构。首版要求两段连续的全槽共同共轭块，旧20条开发训练证书与旧 `sac-07445` 共21例中**0命中**。扩展版允许取逆动作分隔框架开启，以及只关闭部分槽，在 `ms-train-0218` 找到一个完整 **18→16步、work114→104、peak13不变** 的合法重构。真实计分题旧07445仍是15步、work128，没有产生新计分成绩。[summary.json](summary.json) 是最终结果与**两版累计费用**的单一汇总入口，不能把阶段费用再次叠加到该总数上。

该真实命中正是 symbolic_rules 同伴已提示的 `sym-dev-010` 参数特例，属于同一共同框架机制，**不能作为两个小队的独立发现或两项额外收益重复计算**。它不来自旧 donor 四步共轭，也不是旧 `(y,x)` 直接删除。旧阶段的0218普通清理与 donor 宏结果均为18步；这里只给已有证书的开发集重构结果，没有盲测、求解器速度或最短性结论。

|版本与固定样本|原总步数|最终总步数|候选|接受替换|改善实例|
|---|---:|---:|---:|---:|---:|
|v1：旧20训练＋旧07445|345|345|0|0|0|
|v2：同一旧21例|345|343|2|1|1|

## 已证明与实现的规则

对同一 rank 的完整状态，同时把所有关系词以同一 (h) 共轭，记为 (\mathcal C_h)。它与取逆、关系词右乘交换，所以按执行顺序

\[
B_h;P;B_g\quad\longrightarrow\quad P;\operatorname{compile}(\mathcal C_{\operatorname{red}(gh)})
\]

合法，其中 (P) 只含 I/M，且两个纯C块在**每一个槽**产生相同净共轭词。合并后的框架按 (k|\operatorname{red}(gh)|) 个官方单字母共轭展开；没有免费改名或隐去转换费用。

v2维护每槽待决词 (h_i)。取逆可以通过；一次右乘仅当目标槽与 donor 槽的 (h_i=h_j) 时通过；最后按槽展开全部残余框架收费。归纳不变量为原状态第 (i) 槽 (=h_i\cdot\text{已输出I/M状态第}i\text{槽}\cdot h_i^{-1})。生成器不跨稳定化或去稳定化。

完整定义、普遍证明及反例见 [PROOF.zh.md](PROOF.zh.md)。单槽框架、中段额外共轭、稳定化、去稳定化均有明确反例；另有6→2步端点相同但新 peak10004超限的资源反例。短路线必须逐步满足资源限制，恒等式不是验收替代物。

## 实际训练证书

0218的原动作在区间 ([5,10)) 为

```
[13,1,9,2,8] -> [1,2,13]
```

原段在乘法2之前形成两槽共同 (y^{-1}) 框架，末尾只解掉槽0框架；新段先执行取逆和乘法，末尾仍用动作13付费保留槽1框架。入口是精确状态

```
((-2,-1,2,1,-2),(2,1,-2))
```

出口两边均精确为 `((-2,-1),(-1))`。完整新训练证书是

```
[9,11,13,4,13,1,2,13,1,2,2,5,2,8,16,15]
```

其官方ID为 `sac-train-0218`，完整官方验收哈希为 `sha256:6f75ed05c901d3b6d0c10c5aab5ee214a7daa5607400b61e91d9da754e265df7`。完整初态、原动作、逐状态、两次端点匹配、候选资源、接受选择与官方 verdict 都保存在 [results-v2.json](results-v2.json)。第二候选也省2步，但 work106，所以选 work104 的第一候选；两条重叠候选不是两个可累加收益。

## 合成与费用

先执行合成、再扫描旧开发证书。v1覆盖 rank2…8 的21个参数例，包含一份真正到空目标的完整Stable证书13→5步、work90→14、peak13→5。v2额外覆盖14个交错开框/部分关框参数例，完整Stable合成8→4步、work31→9、peak7→3。合成结果不算训练或计分实例新纪录。

|实际执行|search官方apply|verification官方apply|
|---|---:|---:|
|v1合成、反例和资源拒绝|0|1248|
|v1旧21扫描|345|690|
|v2合成与守卫检查|0|251|
|v2旧21扫描|352|704|
|累计|**697**|**2893**|

累计官方apply3590次，官方verify161次；包括手工逐步合成重放、失败动作、官方verify内部调用，以及两版重复的开发扫描。4次执行均完成，没有失败运行或隐藏重试。上限为search250000、verification5000，未重置。符号框架识别与词约简不冒充官方调用，其总操作数未单独计量；候选原语及全部还原动作则全部实际执行收费。

## 复现与证据

首次复现应复制脚本到同级、没有结果文件的新目录，以保留已有证据；同目录再次运行会拒绝覆盖已完成结果。源位置可用 `--official-root /path/to/Andrews-Curtis` 指定。为保持已执行代码hash，脚本保留布局约定：协议在 `../PROTOCOL.json`，源锁在 `../../proof_reconstruction_round2_20261117/OFFICIAL-SOURCE-LOCK.json`。本目录另留[源锁副本](OFFICIAL-SOURCE-LOCK.json)，全新复现布局可把副本放到该位置；不须改冻结代码。按顺序执行：

```bash
python3 check_frames.py synthetic
python3 check_frames.py development
python3 check_pending_frames.py synthetic
python3 check_pending_frames.py development
```

脚本只依赖标准库，核对官方30文件源锁，直接执行核过hash的 `canon/core/stable_core` 源码字节。训练读取先按旧20允许列表过滤，再索引其动作；没有读取新8个测试动作或旧v1保留evaluation动作，没有平台/排行榜访问、比赛提交、原生Yohaku连接或直接GitHub写入。

- v1纯生成器：[frame_rules.py](frame_rules.py)；检查：[check_frames.py](check_frames.py)；[冻结](FREEZE.json)、[合成](checks.json)、[零结果](results.json)。
- v2纯生成器：[pending_frame_rules.py](pending_frame_rules.py)；检查：[check_pending_frames.py](check_pending_frames.py)；[冻结](FREEZE-v2.json)、[合成](checks-v2.json)、[结果](results-v2.json)。
- [累计费用账本](attempt-ledger.json)、[独立复核输入](review-input-v2.json)、[真实训练改善提交文本](improved-training-submission.txt)、[实际方法记录](METHOD-LOG.md)、[文件清单](MANIFEST.json)。

review同伴已用另一份解释器逐状态核对完整有序状态、rank、work、peak，并完整官方verify：旧21例原/终按相同动作去重后22条路线，加两版合成的4条路线，共26条全部通过。其782次官方apply、391次独立解释器动作另记在review预算，未并入本小队费用。[独立复核报告](../independent_review/frames-certificates-review.json)明确只复核最终路线，不冒称独立复现搜索收益。
