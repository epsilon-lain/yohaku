# r6：Stable离路径重合成冻结与接口阻塞（未计算）

## 当前结论
没有新缩步，也没有新有限负实验。旧 sac-07445 完整15步/work128/peak13只是保留的历史合法上界，本轮未重新验收；不称15最短。无平台上传、无查榜。

## 自主问题与冻结方法
从官方原初态在精确有序自由约简tuple上作Stable结构多样性分层beam，rank≤3，生成总词长≤96；允许稳定化、提前删除和暂涨资源。按rank、指数和矩阵和单字母结构分桶，每rank保留512状态，但所有生成状态在beam丢弃前先查空目标精确逆B4字典。正向深≤10，拼接须少于15。无随机（seed0记账），local search cap590000、拟allocation600000 search/6000 verification、wall90秒、producer150秒。拒绝把指数和当精确状态或目标，不免费改名/共轭/恢复。
与旧rank2到U的beam、radius3局部窗、单调两路径闭包、原路径固定DAG不同。本次没有两臂设计，不声称速度因果或测试泛化。

## 拼接正确性与不完备边界
依已实际读取的既有根节点资源签名命题 M-5606eba96406db45@1，若完整合法前缀p和后缀q在同一精确状态z相接，展开长度相加、peak取max，含入口work为W(p)+W(q)-r(z)。候选必须完整逐步重放，不只比较端点。
beam或rank/长度限制会丢掉路径。因此即使将来执行未命中，也只能给冻结实验的有限未命中，不构成15最短证明。本轮没有运行，连有限未命中也不宣称。该段是既有命题应用说明，不是新定理。

## 真实接口阻塞
0/0、无动作的计量接口读取夹具已先allocate。task_submit实际传budget_allocation_id，却返回missing该参数、saved=false、no operation was executed。仅原request查询unknown_task/replay_allowed=false，不重放、不更名绕过。详见r6-tool-argument-block.json.tex和共享 M-8dcd6623caf5ee47@1。
主搜索代码/配置已保存并plan missing=[]，但无compile、execute、搜索输出、CLI或独立解释器回执；meter.verification实际上下文接口仍须读验。独立解释器源码每个原始动作有meter.independent_step，另作相邻消约并拟逐步比较官方trace；同作者实现也不等于独立作者review。

## 理论队反馈、实际阅读与拒用
实际读 M-538c85aecd32c8d0@1（bodySHA a50b3a0eceb10223d436832c493afc5ef06de3a230ea815cdd4de479996d9258）后，不采用其受限C/I最少修复数作为beam下界：本搜索允许乘法M/稳定化S且不携带已知共同frame g及底词U见证，该定理不覆盖这些路径。若强加这个数，可能误剪合法全图路线。本次没有用它改变已冻结代码，因而无伪造跨队计算依赖。
本节点作为不同作者留了解析限域review：核自由积/中央化子与前缀距离论证、各槽计数、残余frame和真实删除重编号、手算7步表及work43；未程序复算、未官方CLI核验、未证明其合成路线全Stable最短。理论成果归理论作者，经典工具来源按其条目保留。

## 来源与公开边界
本轮已读external/mechanisms-20261117/index@1、workflow/MECHANISMS.zh.md@1、SUMMARY.json@1；外部固定commit的11规则、frames v2/010与训练450→372仍是外部种子，不作本机新发现。没有阅读规则全正文，故未采用其具体改写；也未重读旧望月11页。旧v1排除0234/0316/0154/0107保持。
本文是供lain-s-note的本地公开安全稿，非已上传URL；不含私有记忆或数学库正文原文。


### 结束前版本澄清
理论消息随后指出同一条目@2补明rank/槽域、C-I交换和手算tuple尾逗号。本节点已实际读取@2（bodySHA 2a707c86fd8d3438f54d862609b56b936146883091c1765b648452c9efa7d7a8）并另留相同解析限域review；@1历史阅读/review不覆盖假称@2，两个版本不是两项成果。拒作当前beam剪枝的结论不变，未采用入源码。
