# 本轮独立官方CLI与全路径验收

## 结论
本节点是独立验收作者，非应用方法/代码作者，亦非root执行者。固定官方提交 a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e；本次验收真实执行、exit0并确认cleanup。没有发现新缩步：sac-07445仍为合法上界15步、work128、peak13，不称15最短。

|固定候选|原语数|work（含初态）|peak总词长|
|---|---:|---:|---:|
|ac-07445|13|127|13|
|ac-08491|8|48|9|
|sac-07445|15|128|13|
|sac-08491|10|50|9|

固定官方CLI accepted=true，returncode0，stderr空；857字stdout全文已实际读取保存。四条均由官方原初态到各自精确目标（普通AC为有序((1,),(2,))，Stable为空tuple）；程序逐状态比较官方与本节点新写解释器，不只比较端点。普通模式调用锁定core，Stable调用锁定stable_core；没有误用Stable给普通路径背书。

## 独立性、冻结与覆盖
新源files/theory/r6-independent-acceptance.py.tex@ecc031de007afb8539cc10ca833bdf489ff59b8b8075e51f8366d7cf72036042，生成代码SHA86970096a0d2b5590fc8863a3c2ad719a09b8e9290c9f5a066f1d0a18dab792c。协议r6-independent-freeze.json.tex@0bb5cc838ec081116d9cd7841b10b3bb9715503c45a1bede153a6d7996cd87b6（生成SHAc82b97b0240bfa9b0c234563efa8a39f86fd8e74068bde029ece89bd5db11139）；执行前冻结source_set33e9431961bb10ad7043a57b7c31eaeaa443e0af70020d93eeca563bfc0b6dbb、四候选、无随机、失败即停及150秒producer界，无搜索/候选生成/重试。
解释器使用本节点字面动作目录和分治正规形：两半分别约简，只在拼接边界成对消去；不是应用作者的相邻消对实现或复制/改名官方core。D实际删除槽并重编号其余正负字母，顺序保持；S实际增加新槽/生成元。每个独立primitive有from meter import independent_step装饰；全部官方apply、verify及唯一Python CLI子进程位于meter.verification()，子进程保留os.environ可信PYTHONPATH。
覆盖是本批候选调用的0..13、S14、D15..22目录及五个固定guard probe，不是对全部257个Stable动作的通用解释器认证。五probe含S后D、删中间生成元真实重编号、槽号与生成元号不同、其它词仍含被删字母拒绝、负单字母拒绝。四正式候选峰值rank2，probe峰值rank3。所有实际路径核100000动作、总词长10000、work5000000、rank8限制；没有免费改名/整体共轭/稳定化/宏。
恢复器校验固定archive SHA c8ed06893cf895f1221cae149de5b1c4af1657f713aeaf225618723ced9960d6及41文件，再核本轮OFFICIAL-SOURCE-LOCK所有30项。core SHA d2972711dc7008679127a987a8965d41ea1606b0fc50bf67e2e06c71c456b3b5；stable SHA234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d。执行后实际读取两apply函数全文，核普通返回state、Stable返回(state,error)及D guard/重编号；外部代码不冒本机新发现。

## sac-07445完整路径
动作[6,4,12,1,3,6,12,2,5,6,4,2,4,16,15]。初态[[-2,-2,1,2,1],[-2,-2,-1,2,1,2,-1]]。
16态总词长为12,12,13,11,11,11,11,11,9,8,8,5,3,2,1,0，和128、peak13。最后两步为实际D1、rank1的D0，到空。官方与本节点独立16态均实际分页读取，且程序assert与root登记导出的16态完全相等。其它三条独立全轨迹亦实际读取；官方逐态相等由本次执行断言证明。工具对collection统一标complete_field_returned=false，报告保留该标记，不称完整JSON模型阅读；本批选中短tuple值无嵌套遗漏。未读取的新artifact字段不倒填阅读。

## 有限搜索的独立源码/范围审计
实际读M-faadd67bbdf57a62@1、应用冻结协议r6-protocol@81140be245751e7b0cff51e55666e6e43003838e66a2bca4aec7ffdd36c9c812、源码@2bc5723f9984938995783e451065b03f678bce44019304fc83192306cd12f1dc及root世界导出@45dd889e66b59affa58ce0018c6ce0f306f634dadfd424967475f78bd97d77c6；原producer provenance可读并核snapshot/7产物hash/issues[]/exit0/cleanup。原task_result_read以provenance式ID被拒，未换ID绕过或重算原结果；数值正文采用已注册root导出，来源层级明确。
源码从官方初态做rank<=3结构分层多样性beam，接空目标精确逆B4；普通逆边用真实inverse动作，逆D枚举每个插入字母号/槽位并官方检查，逆S只对末尾最高正单字母且其它不含该字母；状态始终精确有序tuple，不把指数和bucket当等价商。方法实质不同于旧资源单调两路闭包、radius3局部窗口、原路径固定DAG。
计数仅源码/回执/导出一致性审计，未独立重跑140329次搜索或逆347行：reported search140329=724逆+139605正，保守issued140352；逆层[1,1,3,26,316]只在rank<=3/总词长<=96内radius4；正向完整1..8层，第9层在90秒guard中断，beam_discard_events99120，joins0/candidate_checks0。600000/6000是原allocation cap，不是实际耗用。无更短候选、无全图不可达/15最短/速度因果结论。

## 理论跨队采用与有限小核证
已实际读M-538c85aecd32c8d0@2。自由因子malnormality、基字母中央化子和末尾A字分解距离证明受限C/I修复最少N=mδ_H(g)+δ_Z(g)+[负号]，再付D；残余t_H与删除rho不能省。该一般证明仍是解析结论，不由有限测试替代。
本节点真正采用该版本给定合成入口/7动作作冻结验收输入：[7,9,11,13,11,16,15]；官方apply与独立解释器每态相等到空，长度12,10,8,6,4,2,1,0，核7步/work43/peak12。此例非比赛初态，也未计算制造共同frame的免费成本；只核既定合成路径，不证明全Stable最短或一般work最优。跨队采用限证书测试，不将仅C/I数作为含M/S且无g/U见证beam的可采纳下界。

## 真实程序与预算
producer project-task-99f870b6bd681e7f0dccff953fb8bceb；request r6-independent-fixed-acceptance-producer-v1；allocation program-18cdbe71f56ee4a53991f8ee，cap0search/5000verification。done/succeeded/ended/exit0、cleanup_confirmed/output_complete均真，stdout1007字节/stderr0已drained，7产物全hash有效、issues[]。
本producer可信reported0search/210verification，保守issued0/216；本地直接official59/independent59，另official.verify46、CLI46合210。共享reported140329/301、issued140352/312、无未决lease（不用差额退款）。结果SHAe7dd8cf639c5adf55dcdda60ec31a8673f54bf68f0722fd8b7422559618bf731；全轨迹SHAf146e191b214f7114b5a106546d3f469f3cbfb81acaf3cba44a64b5e4ada08b6；CLI SHA246aaef1bda420fcc61d914e1cd1ae9171c9866b3ba56f295b794a830d941c5e；合成证书SHAefe6e10222771ccfbce7d093f83752257f6453fd6243e026066860e19d3ba321。
详细绑定、receipt/provenance两种artifact ID、实际选读范围和工具失败均在r6-independent-evidence.json.tex；其导出hash与原artifact hash是不同对象，禁止混同。

## 流程边界
实际model-task-d72eded67cc42e86e4dc23dc047db011，native request r6-independent-official-fullpath-acceptance-v1，thread01a1e99f-c296-7ad0-a485-9f42f82889f6；gpt-6.1-sol/max，900秒96工具。此阶段第5真实准入，保存时剩3模型回合；原截止1794924663.8307414=北京时间22:11:03.831，未重置。未新建/唤醒模型，无平台上传/查榜/重复旧训练清理，无旧望月新阅读或IUT依赖。
