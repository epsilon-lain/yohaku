# 执行与信息来源

本目录由主代理明确指定的云端应用负责人制作，任务、两臂、样本量、预算和停止规则均由主代理及固定 `../PROTOCOL.json` 预先指定。这不是自主发现的团队分工，也不是本机 Yohaku 原团队的续跑；没有连接本机团队、记忆、会话或本机预算。

实际读取的共享材料：根协议；既有 `proof_reconstruction_20261117/check_rule.py` 源码（只作小加载器及经典四步 donor 恒等式参考，未覆盖）；缓存官方 `core.py`、`stable_core.py`、`canon.py`、`stable_training_424.json`、`training_manifest.json`、正式 `data/manifest.json`；官方 `sample_submission.txt` 的文本格式示例。没有打开 `structure_discovery_next_20261117` 下的文件，也没有读取或分析协议排除的四条旧 evaluation 动作数组。公共训练 JSON 整体解析后，仅按 ID 过滤才访问获准动作；冻结选择只访问 ID 和声明长度。

理论队发来的编译次序被实际用于实现：若 h=(a1,…,am)，先按 a1^-1,…,am^-1 对目标作字母共轭，再执行四步 donor 共轭，再按 am,…,a1 共轭。理论队同时确认三步左乘 `[I_i,R_{i,j}^{-s},I_i]`。这些是明确消息协作；既有 donor 恒等式不主张为新数学发现。

应用负责人提出并落实的程序决策：用精确完整有序状态（tuple 长度同时编码 rank）为每个后续位置建索引；遍历所有起止窗口，不要求最大连续共轭块；所有 257 原语 ID 都交官方 apply 检查适用性；按展开长度跳过不可能严格缩短的宏；宏中每一步各调用一次官方 apply，不把宏作为单步，不以独立代数式免费算终点；按完整新路径 length/work/peak/start/end/expanded moves 排序，对最优可行候选做完整官方 verify 后才能接受；同终点使后缀严格复用，work 包含初始态一次。候选的中间长度资源检查和全路径 verify 双重保留。

首次实现 revision 1 在主代理审读反馈抵达前已经做了一次 synthetic 和 10 个 development armcases。其原字节源码、结果及 ledger 保存在 `raw-v1/`，哈希清单为 `REVISION-1-PRESERVED.json`；本机另保留同内容 zip；公开包保留全部原始文本。它没有访问新 test 动作，也没有冻结。

主代理审读指出四项实现问题并要求冻结前修正：训练数据标签 ms-train 与官方 Stable 提交 ID sac-train 要分开；真实提交文本用 `ID: [moves]`；应直接 compile 已核哈希源码以避免读取陈旧 pyc；全局 search 总额要包括诊断和开发重试。revision 2 完成这些修正后重新做 synthetic 和 development，结果的长度/work 不变。预算始终用原始 training source ID 累计，ID 变更没有重置计数；两次开发尝试、两次 synthetic 的调用都留在当前 `attempt-ledger.json`。revision 1 的训练证书哈希使用了错误 ID，不能作为可提交的官方训练证书；主结果只采用 revision 2 的规范 ID。

未改变实验候选库、全局排序、样本选择、预算或最多三次接受的规则。应用完整 verification apply 额度为 25000，另预留理论 2000、主代理独立复核 3000，共 30000；应用执行器自身只扣前 25000。开发重试使用同 armcase 的剩余额度，诊断和重试同时计入 2100000 全局 search 总额。对照的是相同预算上限，实际耗用调用数不同；不将墙钟时差解释为因果速度改进。

冻结文件记录脚本、配置、协议、来源哈希及 16 个固定 test ID；先写入 `FREEZE.json`，再由 test 子命令核验全部哈希并写 `TEST-ACCESS.json`，随后才索引这些新 test 的 moves。冻结后不改脚本或配置，不按结果扩大样本。此实验是给定已知解的证明压缩，不是从头求解，也不是原 v1 solver 对照。

实验结束后，主代理消息提供了一项事后机制解释：所有 7 个改善案例均在精确入口 `(y,x)`，旧六动作 `[0,2,5,2,8,16]` 与单动作 `[15]` 都到 `(x)`，再接旧后缀 `[15]` 到空。它们共同绕过了先规范成 `(x,y)` 的多余中间目标；不是七种独立机制，也没有体现新 donor 宏收益。此解释来自主代理的独立 63 路径复核与官方 CLI 验收，未用于更改应用代码、配置、test 选择、结果或重跑；只在实验完成后补入说明。主代理报告独立复核及 CLI 共 2026 官方 apply，理论另报 1716，均由根报告合并，与应用自身 ledger 分开。
