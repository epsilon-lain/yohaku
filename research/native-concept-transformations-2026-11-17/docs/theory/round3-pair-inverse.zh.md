# 第三轮理论中文稿：非单射表示的目标信息与恢复成本

# 只保留二元合取观测：独立集原像、目标辅助位与探测分离

## 模型与旧结果的改变
固定有限简单图H=(V,E)，V={0,...,n-1}，逻辑独立原子对象为真坐标集合X⊆V。转换只输出F=T_H(X)={ij∈E:i,j∈X}，丢弃原子直接观测；H已知，所有边观测完整、无噪声。旧M-98718cbca95c0dc3@1保留原子并添加pair名字，故守完全信息；本题真正删去原子，继承pair-AND语义但不把旧最短描述/matching结论当作恢复定理。没有运算串重命名或AC改路声称。

## 定理1：可识别结构及全部原像
给定任意F⊆E，P为F全部端点，Z=N_H(P)\P，R=V\(P∪Z)。
F可实现当且仅当F=E(H[P])。成立时，全部原像恰为
T_H^{-1}(F)={P∪I:I为H[R]的独立集}。
证明：每个正边端点必须为真，所以P⊆X；P内部任何边也须为正，给必要条件。任一P外邻点若真，会产生端点不全在P的新正边，故Z全假。剩余真点I⊆R不得含边，否则产生F外正边；而P与R间无边。反过来上述任意独立集满足恰为F，且X=P已经证明充分性。识别F合法只需由正边收集P，再扫描E检查F=E(H[P])，O(n+|E|)步，不必先恢复X。

## 定理2：指定目标的精确歧义
指定S⊆V。目标一为坐标模式g_S(X)=X∩S，目标二为其重量w_S(X)=|X∩S|。记i(G)为独立集个数（含空集），α(G)为最大独立集大小。
在可实现F上，令A=R∩S。模式目标值恰为(P∩S)∪J，其中J遍历H[A]的全部独立集；故值数i(H[A])。每个J可用I=J扩展，不需要猜R\S。
重量目标值恰为|P∩S|+{0,...,α(H[A])}：最大独立集的所有子集给全部大小。两个目标都能仅由F唯一确定，当且仅当R∩S为空；完整X唯一则需R为空。例：H边01、12，顶点3孤立，F={01}，P={0,1},Z={2},R={3}。S={0,1,2}的模式110和重量2已经确定，但完整对象仍有两个原像。这区分了目标求解所需信息与完整恢复。

## 定理3：最坏辅助编码位数
辅助模型严格定义为：编码器知道X，解码器知道H,S,F，收到固定长度b位消息后只须输出指定目标；双方使用一个预定有限算法。消息内容不限定为原始坐标，编码/解码计算不在“消息位数”账本内。
一般有限映射T与目标g的精确位数为
ceil(log2(max_y |{g(x):T(x)=y}|))。
下界：同一个y下不同目标值必须收到不同消息。上界：对每个y将可达目标值按预定顺序编号，使用共同最大长度的二进制编号；非对应编码可拒绝。此是标准有限零错误编码计数的应用，不是文献首创或算法效率命题。
应用本题，由定理2及诱导子图单调性，零观测F=∅已经达到最大歧义，所以
b_pattern(H,S)=ceil(log2 i(H[S])),
b_weight(H,S)=ceil(log2(α(H[S])+1)).
恢复全对象取S=V；并非每个目标都须支付完整对象的辅助位数。实现模式编码可枚举H[R∩S]全部独立集，对J取字典序rank/unrank；实现重量编码取|X∩S|-|P∩S|。最优位宽的α/i及rank表可能需要昂贵计算，编码器知道X也不是免费求解器。

## 定理4：只准直接探测原子时的严格分离
另一种恢复模式中，没有任意辅助编码器，解码器在见F后只能自适应询问某个原始坐标x_i，每次1次探测，要求所有X上的零错误确定性求解。允许探测S外坐标。
只要S非空，模式和重量两目标的最坏最优探测数都恰为|S|。上界直接询问S。下界在X=∅、F=∅的全零回答路径上，若某i∈S未问过，X={i}仍给同样F和全部已问回答，但两个目标都不同。因此必须问完S；S为空时为0。
取H=K_s,S=V,s>=2：零观测原像只有空集和s个单点，其他可实现观测唯一。因此完整恢复的最坏辅助位ceil(log2(s+1))、重量目标1位，但两者最坏直接探测都为s次。这不是同一操作集合的算法加速比较；它反驳把“少量任意辅助位存在”直接解释为“少量原子探测即可找到它”。

## 分账而非总分
定义账：若沿用旧树计价，各pair定义正文3节点，总3|E|，绑定头0；只是声明的定义价格。
转换账：持有X者生成全部观测用|E|个二输入AND评估；不含先取得X的代价。
辅助账：以上固定长度消息位数，不含编码计算。
识别账：检查可实现性O(n+|E|)边/顶点扫描。
恢复账：通用模式rank/unrank可枚举至多2^|R∩S|候选，再验独立性；不宣称多项式最优编码。重量编码虽计数简单，最优固定宽度可依赖α。
探测账：另一个受限操作模式的最坏|S|次直接原子询问。
这些单位和前提不同，不自动相加，也不从完全图的位数差宣称总成本/搜索/token收益。

## 本次边界
只处理完整无噪声pair-AND、独立Boolean原子、简单图及指定模式/重量目标，不处理背景蕴含、负文字、随机有错恢复、一般图商路线或比赛路径。基础“单点和零观测混淆”在旧结果已存在；本次新增是全部原像的独立集结构、可实现性检查、目标特定的精确辅助公式及与探测模式分离。一般定理来自上述证明，有限核验只补充支持。

## 补充：点态探测一般推论

更精确的点态探测推论：在合法观测F给定后，两目标的最优最坏坐标探测数均为|R∩S|。上界只问残留目标坐标，其余目标坐标已由P/Z固定。下界在原像X=P的全零残留回答路径上，任一未问的i∈R∩S仍可取X=P∪{i}；它保持F却改变模式和重量。因此必须问完R∩S。该一般证明补足全局|S|结论；新代码对n<=4的每个合法F/S分别用任意坐标分支的minimax决策树DP检验，允许问S外坐标，不预先把剩余原子全问作唯一算法。

## 真实原生有限核验

一般证明 M-a85fc42f1e3e61a9@1；完整代码/冻结配置/有限结果和点态推论 M-5500b5711f684faa@1。

task project-task-8af630bd59010ae18cf545ad37f18415 / request r3-theory-pair-inverse-v1-20261117 / action native-theory:round3-pair-inverse; snapshot/source_setc0e58442b566c2d83a6f87654c82a22f031543810b9f370caeec9ea95557079b. Source round3-pair-inverse.py.tex@4e019c9408063de1ad4b5226200f157ff0789e28b72732563ce1ce0b7b7cbb9b generatedSHA4249f2bf1486064466bcc046ccb761f776a9b8a7339ee2d13ab829a67e0a107c. Freeze source@46d2f791ad2c7629be90b86b7b8da86031686886f5a848167c1bec76c10f023d generatedSHA0909e396a94bc3b0385adf1efbb3ef26213a248f5b420648ca065a3358771e25. Artifact round3-pair-inverse-results.json IDartifact-df30dbe712d0faedfba1386fd529ad799362de10d0a458d26fc328b49ac5cb79,5350386bytes,SHA1a7a556eadc1c1d1015a14f3cc201146259829610b0393ffaf3d95823e6bd317. Provenance snapshot/artifact valid, receipt exit0/cleanup confirmed/output complete; stdout1427bytes drained,stderr0. Program-observed4.600438370005577seconds is program runtime, not inference cost.

逐n原始统计：
```text
{"n": 1, "graphs": 1, "object_count": 2, "output_subsets_examined": 1, "realizable_outputs": 1, "target_fiber_cases": 2, "codec_replays": 4, "query_DP_instances": 4}
{"n": 2, "graphs": 2, "object_count": 8, "output_subsets_examined": 3, "realizable_outputs": 3, "target_fiber_cases": 12, "codec_replays": 32, "query_DP_instances": 24}
{"n": 3, "graphs": 8, "object_count": 64, "output_subsets_examined": 27, "realizable_outputs": 24, "target_fiber_cases": 192, "codec_replays": 512, "query_DP_instances": 384}
{"n": 4, "graphs": 64, "object_count": 1024, "output_subsets_examined": 729, "realizable_outputs": 425, "target_fiber_cases": 6800, "codec_replays": 16384, "query_DP_instances": 13600}
{"n": 5, "graphs": 1024, "object_count": 32768, "output_subsets_examined": 59049, "realizable_outputs": 15312, "target_fiber_cases": 489984, "codec_replays": 1048576, "query_DP_instances": 0}
{"status": "passed", "clique_examples": [{"n": 1, "object_aux_bits": 1, "weight_aux_bits": 1, "proved_worst_coordinate_queries": 1}, {"n": 2, "object_aux_bits": 2, "weight_aux_bits": 1, "proved_worst_coordinate_queries": 2}, {"n": 3, "object_aux_bits": 2, "weight_aux_bits": 1, "proved_worst_coordinate_queries": 3}, {"n": 4, "object_aux_bits": 3, "weight_aux_bits": 1, "proved_worst_coordinate_queries": 4}, {"n": 5, "object_aux_bits": 3, "weight_aux_bits": 1, "proved_worst_coordinate_queries": 5}], "elapsed_seconds": 4.600438370005577}
```

以上有限范围通过，不替代任意图的证明。对象直接枚举、独立集原像公式、实际编码/解码回放和minimax决策树DP均由同作者实现，不能称独立同伴review。一般理论M-a85fc42f1e3e61a9@1现已获root精确正文的独立解析review；新数值没有独立重跑，后发M-5500b5711f684faa@1点态推论不自动在该review范围。产物完整保存全部合法原像对象、各目标i/alpha/位宽与范围信息；模型没有逐字读完5MB产物，只实际读取完整stdout并由provenance验哈希。

## 沿革、组织与发布边界
本轮USER全文来源round3-external/task/CODEX_TASK.md.tex@05ca617e98650e698e62d56d76ddc901c6e7d615a6d875fd8e6b9a6999351c32。数学模型由理论负责人自主选择，群seq46先报范围，未强制增员；旧图证书/成本结果不重算。只新增round3前缀源/action，manifest编辑前重读revision，保留root并发新增源和所有旧actions。本题计算完成后，又索引并完整读root商路线M-2425cab292392fd9@1并独立解析review1377；这只是后续交叉复核，不倒填为本题的先前输入依赖。
旧pair-AND精确正文及review921实际读取：沿用独立原子/合取语义、明确定义价格；旧一般证明已独立审过，但不称旧1099有限数据重跑。新转换删除原子，而不是把旧串换名字。定义、转换、辅助、识别、恢复与探测账均保留不同单位，不计算未定义总分或token/搜索收益。
旧阶段root原生超时/error/stop与账本保留，新阶段独立准入。Stable08491=10的后续外部完整复核不变成root原生成功；不要求该已证规格<10。
此稿面向epsilon-lain/lain-s-note待宿主审阅公开；过程包面向epsilon-lain/yohaku。当前仅有已保存的Yohaku本地入口，没有声称已push或新的公开URL。没有比赛平台上传。

## 安全边界后的状态补记
root独立review只认可本题M-a85@1的一般证明，并选读产物size_summaries/clique_examples/proof_dependency及查provenance；不称完整5MB人工审阅、独立枚举或完整代码审。后发点态推论在M-5500@1另有完整证明，但未被这次root review自动覆盖。
本理论任务已在新阶段shared_stop出现前完成。随后root与应用的新task_submit遇到门禁拒绝，不能把其未运行稿算作本理论的成功计算；新运行需宿主检查，绝不清旧stop/换ID绕过。旧阶段原生失败/外部补核来源仍保留。当前小题已闭合，不因有限核验成功而扩大计算。
