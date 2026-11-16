# 本轮应用过程包索引（供 yohaku，尚未公开发布）
数学中文稿：files/application/round2-application-science.zh.md.tex。
本地原始提交：files/application/round2-submission-local.txt.tex；完整官方stdout：files/application/round2-local-official-verdict.json.tex。
本索引及上述入口需read-back核验存在后再向用户报告；没有新公开URL/平台上传声称。

## 身份、用户目标、状态
node ai-node-0299a356d74db83b9ab4ebc7，应用方向负责人；本轮由新的USER event482触发，不是旧AI续题。权威目标round2-external/USER-GOAL.txt.tex@9919897d9dec467f2b6f6f8e67f9c5d229ee462a8af20a8e4a91e30d8501a779覆盖旧执行包不一致目标。
本轮模型task model-task-8651f3dda6a052c0a635b977b4c2fb98，node request round2-application-user-handoff-v1。当前采样时running；只有final后root沿同一ID核验才能称done/cleanup。本人不重放、不重置旧预算。
requested_profile与native model_settings均回读openai/gpt-6.1-sol/max；任务预算1800秒/128工具。此为请求/配置回读，不是未暴露供应商推理身份证明；费用unknown。未新增节点/模型，保留全部首阶段源/actions/任务/数学版本与失败。
普通AC最短路径只作回归；实际目标是Stable严格少于旧10/15，不拿work/token改善替代。

## 真实task区分：准备 != 开始搜索 != 球完整 != 全局结论
1. 准备（非研究结果）：project-task-3628c3c7ed6347e97c261d4b4cca3528，request app-r2-official-semantics-inspect-v1，round2-inspect，exit0。恢复41文件并读官方Stable正文，旧四路径合法验收。snapshot4b2e4c4c8ecd599620caa21e6536259cd4eac3f61188a5bcd8e2f7ab156d95d5；r2-inspect.json SHA974f2d986e88d5057fc68a3d24a21c4106c97c7dd0d43e4d4c64478439405760。
2. 首个真实改路搜索：project-task-c9c87a1852351c9edf11c3dae503cb7c，request app-r2-stable-prefix-bridge-search-v1，round2-search；exit0，cleanup/output complete，provenance四产物valid。snapshot4b082b84b2d4c97ec2e990c936ae337d40787bd17ef4e83ae46135f8c3625678。111595次apply，无guard，未改善。结果72366db9c7071c40f7e8ec20b521c53028b272881080d5f4530b843d658c7ed5。
3. 作者全局Stable08491证书：project-task-802847184ed0526eb3fa4966f91e216e，request app-r2-s08491-rank5-complete-certificate-v1，round2-rank5-certificate；exit0、cleanup/output complete、provenance五产物valid。snapshotd4fb5d2f82f1ceb38f812e507f5492c723add55977249fec4d36f85adc4d9adb。76016次apply，球完整28511/6081空交；秩界将rank5下界升成全局<=9排除。结果81ef5efe968cef8e9a00b2eb0f4fa6188b060c1293613690f49abbf847dd12ad；完整球bc18a78605cf2a979179c096f32616e580b2f2483b1035f99795816d2cd722fb。
4. 更深07445搜索/截断：project-task-0996b6d2018bdfc65fb43b4deee6ad38，request app-r2-s07445-prefix3-deeper-v1，round2-s07445-deeper；exit0、cleanup/output complete、provenance四产物valid。snapshot40d1c1c91755d170ce6ff2aaabd5187d3c28caba6aeea2bb9ea9db03d74d5600。1178050次apply，空逆B6完整130799，正B5触350000帽，只完成4层；未改善且没有完整下界。结果0919f036fce33bc884ffb584dfd04dd8d2c3f2481191560cc30ce226f0a87d55。
以上研究调用合计1365661次官方apply（111595+76016+1178050）；不把恢复/全路径验收/CLI额外调用隐藏成研究步数，不将本地秒数解释为普遍算法优势。

## 冻结源/actions与数学版本
- round2_search.py.tex / round2_protocol.json.tex / action round2-search；先发表完整预注册代码M-dbf5d18ecc73c3f2@1，后结果M-74a3dba7e33b566b@1。
- round2_cap5_certificate.py.tex / round2_cap5_protocol.json.tex / action round2-rank5-certificate；先发表秩界/冻结代码M-1023ab8fc5b64f65@1，后全局距离10作者证书M-f0cf804edb119bae@1。
- round2_s07445_search.py.tex / round2_s07445_protocol.json.tex / action round2-s07445-deeper；先发表M-b1aec144ae2b6c9a@1，后未改善/guard失败M-39f8e73ed6e50245@1。
所有源.tex经revision检查/Loom生成，task_submit前project_plan无missing，沿稳定request ID提交；没有未知重放。旧compute/umbrella-verify均保留；恢复资源的.tex/b64明确加入manifest，不把可读文件误当自动带入快照。
各研究task的官方CLI包SHA均793d179a5bff524505b44f081abeec197d2b49820d0a60f0e9c635d43db79399，提交TXT SHAa5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2，旧prefix字典SHA0d63c6b137863ab80f10da720d0e57f3c597346d6caa7a51cf87c79e2a0adbfe。
完整source/macro/output/artifact映射沿各task_provenance保留；结果JSON可由task_result_read精确指针分页读，不复制大二进制。

## 实际组织、消息与知识采用
先读权威记忆@9d35a081...、resources与math索引、新USER目标/工程入口，再自主发群seq25选“短段/桥接”题；没有用户预设固定流水线，也未增员。
root群seq28的资源提醒已实际采用为完整候选官方重放与CLI，采用事件755指向round2_search.py.tex；M-5606eba96406db45@1正文在首阶段已实际读/审，本轮没有伪造新增正文读取事件。其一般组合定理不是距离10下界所需的新前提。
工程external/native-compression-next-20261116-02-resources@1本轮实际读；adopt事件753指向新源及真实恢复任务，后续41源hash恢复和官方执行形成单独产物证据。工程种子不算新研究。
rank3完整负结果引发本人自主提出rank净变化引理和新rank5 task，旧源/负结果未改写；得到08491精确10后主动停止撞该例，并新冻结07445 prefix3更深搜索。触预注册状态帽后如实发表失败，未悄悄提高帽子、没有将partial空交当证书。
理论M-98718cbca95c0dc3@1等本轮新内容仅收到群摘要，应用未读正文、未采用，不虚构互相帮助。root已收到全局10作者证书的独立复核邀请；当前独立结果仍需真实到达后另记，不冒称通过。
共享群ai-chat-7a7abc9f19d2de24731c6b27，无wake造成额外准入。所有本轮新条目由math_publish自动ID生成，未复用旧自拟无效ID。

## 运行后显式勘误及限域复核
# 本轮rank文字勘误（不改原快照/产物）
触发：总负责人共享群seq41在运行后指出cap5结果中limitations仍有“rank cap3”。本人实际按产物精确指针读取，确认：
- project-task-802847184ed0526eb3fa4966f91e216e 的r2cap5-search-results.json SHA81ef5efe968cef8e9a00b2eb0f4fa6188b060c1293613690f49abbf847dd12ad；
- project-task-0996b6d2018bdfc65fb43b4deee6ad38 的r2deep-search-results.json SHA0919f036fce33bc884ffb584dfd04dd8d2c3f2481191560cc30ce226f0a87d55；
两者/limitations非执行文本字段都残留“rank cap3”字样，系从v1复制时未同步替换的描述错误。
实际控制搜索的冻结protocol.rank_cap分别是5、8，运行ball metadata亦分别rank_cap=5、8。BFS的normal/forward和逆destabilize插入均由该CFG变量生成；完整cap5球28511/6081、深搜索逆130799和正350000截断对应正确执行cap，不能以旧非执行尾注把它们误读成cap3结果。原v1本来确为cap3，没有此勘误。
原源、完整源码发表版本、运行快照、全部artifact哈希均保留不变；本勘误是后发显式记录，不无声改旧产物，也没有重放旧请求。结论及guard范围不变：08491作者证书以cap5+已证秩界闭合；07445是cap8下正球截断，仍无最优证明。该文字勘误不替代独立复算。
理论负责人对M-f0cf804edb119bae@1的review仅核rank计数和条件双球逻辑，未审官方/逆源码/数值/CLI；不能宣称完整distance10已获其独立复算。root正在另选全257动作逐一试行/不同label-lift的独立核验，真实回执尚未由本文读到。
正式勘误条目：M-7202b98c9b996e05@1；原产物和快照没有改写。
