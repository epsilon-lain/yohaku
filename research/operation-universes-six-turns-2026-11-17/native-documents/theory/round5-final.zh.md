# event2974 / round5：最终限域证据核对

## 结论先行
本授权已实际接续原理论、应用两方向，产生新的解析结果与一次新的有限局部变换实验。理论证明的公开稿已保存；应用没有严格原始步改善。此续行仅闭合此前登记的证据，不另选数学题、不开搜索、不重跑程序、不增员，也不默认耗尽余回合。

## 1. 真实终态与失败保留
本段仍使用event2974的总6回合/90分钟授权，首准入北京时间2026-11-17 16:34:54.181718，固定截止18:04:54.181718，不刷新。资源工具中的阶段后缀02不是第二份授权。当前root核读任务为model-task-dc03f633f8275d9a505e58c3c2ae9d00，实际配置Sol/max、900秒/96工具。

按原request ID单次查实：
- 原root model-task-211094b3d3222c097a91830a2c75434c：error，900秒超时；execution ended，native进程已回收、cleanup完成。不是done。
- 理论model-task-08881865217c057e5161d0032de2b91d：同为900秒超时error/ended/cleanup完成；已保存文件与数学条目保留，不能因它们存在而改写模型成功。
- 应用model-task-766b2092f70db6957eb4959a1eed5e90：done/ended/cleanup完成。
三个原任务实际配置均Sol/max、900秒/96工具。旧stop、失败与账本未修改，未重派。当前root自身最终进程清理只有本turn返回后才可由宿主确认，不预填。

## 2. 已保存的新解析数学及原独立复核
- **Root M-ca883c95076f9d74@1**：有限域线性操作库的交叉交换条件下，组合可观测空间维数r≤r_S r_T；已保留U⊆W时，若编码者仍能访问原输入，升级所需固定长度零误差消息恰为ceil((r−dim U)log2 q)位。原输入已删除后，丢失信息不能靠后处理补回。网格给紧例；指定正向移位/同价转置对照没有净收益，不是物理时间或一般算法下界。原理论负责人独立解析review3524；不是root自评或本次新复算。
- **理论 M-3e7ea6919b89bec9@1**：等幅三符号四类手算证书，联合目标2位，而强制先以最优1位立即交付A的两阶段最坏3位。仅固定长度、零误差、无免费长度信道模型。原root独立手核review3546。
- **理论 M-544497afb1b8963c@1**：非零signed inputs、公开正幅度；超边绝对和的局部符号可分离RI条件下，联合辅助信息R=n−c(H)+rank D，D记录乘积子集与分量交集奇偶性。RI下条件增量是秩差、信息成本次模；任意幅度仅上界，幅度全局最坏精确。原root解析review3549。编码/解码、识别RI与运行成本未定量，不能转述为计算加速或比赛收益。

上述review作者、原task、精确版本与范围已在共享库核读；这次不重复记作新独立证明。旧M2149的理论review3428、旧Me3的root review3435也只是其各自解析范围。
数学稿：`round5-root-commuting-upgrade.zh.md.tex`、`round5-joint-amplitude-targets.zh.md.tex`，均在files/theory下。

## 3. 应用：合法资源条件与完整小负结果
**M-c398c4f1100cb45e@1**的条件是精确有序入口/出口，不是商代表。相邻交换只把中间态u换成v，故步数不变、Δwork=r(v)−r(u)；r(v)≤r(u)保证work/peak不增。删精确二步环才少两个原始动作，Δwork=−r(u)−r(x)。需要r≥0、状态包含全部合法性信息；额外逐字/rank/history约束须另核或全程重放。root本次独立解析审阅3897只确认这些条件化恒等式。

唯一producer **project-task-c0f44bc9f068248f856aa641a7c3aac4**，request app-r5-07445-monotone-diamond-v1，done/succeeded、exit0、cleanup_confirmed、output_complete；snapshot/source_set：
`fa80ff558a1cbf299854a57601d3fb42ed0e83321606a2385de1f6e94c3512b1`。
provenance核六产物逐hash有效、issues=[]。源码/协议当前revision及生成hash与该快照相符，共享预发表程序与权威源码文本一致。

**M-39a75836f7c581b4@1**记录冻结方法类完整排空：
- 两条路线、两条完全处理、queue=0、guard=null；28邻位，32实际包装apply，缓存22另列。
- 交换失败分解：首步不合法2、次步不合法2、出口不同20；精确同出口4，其中增work2拒绝、非增2（一条新增、一条回到已见）。
- 没有二步环、没有缩步；两路线均15步/peak13/work128。新路线仅交换零基offset5的[6,12]为[12,6]，中间资源均11、Δwork=0。
- 无beam、无触帽，不覆盖暂增work再下降、插入、其他替换或所有Stable路线，**不证明15全局最短**。

root本次读完整冻结搜索源码/协议、全部summary计数、两证书行和新交换完整证书、基线与当前16态、candidate及acceptance29项、相关资源源码摘录和完整CLI。独立限域review3899确认源码/产物/回执的一致性；**没有独立运行、另写实现或把28邻位逐一重新计算**。原作者自检、此次独立核读与独立复算明确分开；仍是同一个producer，不计第二次实验。未声称整份JSON无遗漏人工通读。

## 4. 完整CLI与可提交文件
本producer的CLI returncode=0、stderr为空，stdout857字符已全部读，accepted=true：
| 实例 | 原始步 | work |
|---|---:|---:|
| ac-07445 | 13 | 127 |
| ac-08491 | 8 | 48 |
| sac-07445 | 15 | 128 |
| sac-08491 | 10 | 50 |

新增等cost路线B有完整official.verify，但没有单独CLI；最后按冻结排序仍提交旧路线A。普通8/13及Stable08491=10仅回归；08491最短10的外部完整复核来源不改成本机新发现。

可提交文件：`files/application/round5-submission-local.txt`，196字节，world全文读回与producer哈希相符：
`a5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2`。
结果JSON SHA256：`ee1376b9035c9b59caeec9192dd67c06ec337740f368d03509772f1d9a442d84`；
CLI JSON SHA256：`a4160c60722f357c8825d2243deccf04df6060272e03cf870fc0819713e5b925`。
官方规则固定于a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e，仍属external工程来源。包装验收里的native_receipt=false保留；真实隔离执行由原生task回执另证，不篡改包装标签。不上传、不查榜、不报因果速度/token收益。

## 5. 文献：本轮读取与历史导入严格分开
早前11页导入映射不是11页本轮新读。原root本轮实际读资源索引、PANO11精确@1及对应权威.tex，已在原literature receipts留证。理论本轮process明确报告重新读资源索引与IUT I第12页@1；应用本轮process明确没有新PANO/IUT页读，旧PANO38/39/40不计新读。本次root仅核读这两份process与元数据，**没有重读原页，也没有逐原始工具事件重建head阅读日志**。

PANO官方URL：
https://www.kurims.kyoto-u.ac.jp/~motizuki/Panoramic%20Overview%20of%20Inter-universal%20Teichmuller%20Theory.pdf
PDF SHA256：eb42575f73d69d1f28e949eb9e52593dd17d1b85c15cc8b44fdfd12ae86b708b。

IUT I官方URL：
https://www.kurims.kyoto-u.ac.jp/~motizuki/Inter-universal%20Teichmuller%20Theory%20I.pdf
PDF SHA256：7360e3ed27c235b5497a0743d3ed1646fbb97688547d16b7c784fc7f127f1f03；
第12页条目正文SHA256：71fc0a335c84194b95d57eaf81096668728ae961d19c4d6f29c4a4b4ef018721。

这里只用可辨散文提出结构保留/信息重建问题，未建立IUT到这些模型的数学或复杂度桥梁；CFF/提取公式仍未认证，不能当证明前提。IUT II–IV未取。本稿不复制整页/PDF、私有记忆或原始聊天。

## 6. 交付与停止边界
本稿和更新的`files/theory/round5-process-index.json.tex`、`round5-literature-receipts.json.tex`、`round5-progress.zh.md.tex`为总入口；应用详稿为`files/application/round5-public.zh.md.tex`、`round5-process.zh.md.tex`。本稿的精确数学版本采用另留，实际源码/产物依赖单列，不倒填历史依赖。

已保留index(limit=10)失败；随后省略limit成功获取结构预览。预览不是完整证书读取，也未因此重提计算。
仓库由HOST筛查并另留发布回执；这里没有push回执，不声称已发布或上传。实际供应商身份与费用仍unknown。小核对稿已提前保存，最终只完成既定证据边界，保存记忆后research_finish；不再排续行、等待模型或追加搜索。
