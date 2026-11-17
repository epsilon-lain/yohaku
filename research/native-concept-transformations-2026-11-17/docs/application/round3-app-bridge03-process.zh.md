# 安全桥03应用侧交付与证据索引

## 有限任务和组织决定
本次USER仅要求读取已执行封存程序，沿原3小时/总turn，不重置、不重跑、不改代码协议/预算。应用负责人自主限域：源码/协议/结果/checkpoint/CLI对照及手工计数，不新开理论或搜索。群seq67先声明，seq69报告逆球读取限制；root群seq68仅提醒计数器口径，与本人源分析一致，未因此改变算法。原作者/方法选择仍应用，root仅执行；本次无独立复算review。

## 真实task与冻结源
- task：project-task-f3037adff007a0a53e60c6491983d93d。
- request：root-app-r3-07445-frozen-delayed-bridge03-v1。
- action：native-application / round3-target-search。
- snapshot/source_set：2c3db8649a4359d58446f4e834afc34afabccdd7e2a38da3055a831ddae64d95。
- 源round3-target-search.py.tex revision83729b0a652916bc94e2e23d8602e86fa92b6c4f0054c0826669f023b76ae561；生成SHAe014ffc2c90c77a79c4cea2ea8601029ab18c8d6cc1cc5b2e50e134f84e1786a。
- 协议round3-protocol.json.tex revision176395c299be95781e67506f5af0b5d11a7dbbde4058cc67d6709bd44ed5a7f5；生成SHA50e4947c3e3458d2f854b07a34224befdc24ec3180c68de9d22715977e0080a7。
- 原生status done/succeeded/exit0，execution ended，cleanup_confirmed/output_complete=true；stdout1822bytes已按字节读取完，stderr0bytes已读完，不重置游标。

## 原产物（保留稳定身份，不复制12MB证书进模型）
- project-task-f3037adff007a0a53e60c6491983d93d:round3-results.json；9416 bytes；SHA256 68d994ea5391a887753b7ab126cd89d666f124733bab00f568e5fb622c4ed6d1；provenance valid=true
- project-task-f3037adff007a0a53e60c6491983d93d:round3-reverse.json；12517205 bytes；SHA256 7c0ee1286f1529a269af2d8d665243ff1f9b841f233b763ee575274041731ed9；provenance valid=true
- project-task-f3037adff007a0a53e60c6491983d93d:round3-checkpoint.json；1773 bytes；SHA256 78819eff5faff568936bd9808b4aced6a73728a6107fac97780cd809e696b28d；provenance valid=true
- project-task-f3037adff007a0a53e60c6491983d93d:round3-candidate.json；177 bytes；SHA256 b3674e9483d9bd5ee0a2730f88eeab27cd954b580e898702d0397bae8ec39063；provenance valid=true
- project-task-f3037adff007a0a53e60c6491983d93d:round3-submission.txt；196 bytes；SHA256 a5061ca016dd710a8a0ea2909bba1a08a796b2c6a75152ee0019d65408c969f2；provenance valid=true
- project-task-f3037adff007a0a53e60c6491983d93d:round3-cli.json；1004 bytes；SHA256 a4160c60722f357c8825d2243deccf04df6060272e03cf870fc0819713e5b925；provenance valid=true

## 读取/核查范围与具体限制
round3-app-bridge03-reading.json(.tex)保存所有结果字段投影、checkpoint、候选、CLI、source mappings、六产物provenance摘要和逆球读取拒绝原文。此投影不是原results.json的字节副本，不冒称complete_source_read_by_model。实际读取所有21个头字段，acceptance按0/16两页读完29项；结果与checkpoint层/303283/null一致；协议对象与冻结源解析一致。
原results内部reverse_word_ball.sha256=4b26b0fb328aac1aff08b64de041fc724053b20c7941c30a5c341a162cab4c50，是排序状态集合编码SHA；与完整round3-reverse.json文件SHA不是同一编码，不可混用。尝试该文件/states offset0/limit3被result_size拒绝：Result must be a regular file no larger than 8 MiB。未读正文，无独立B5重算。没有修改原文件、绕限制或为分片启动新任务。
源码审阅：矩阵仅必要下界且完整word key；try_join先精确回放到U再验整条稳定动作；无winner回落冻结15。单路径lex去重不是累计资源前沿；join尝试/失败数没有单列，不能由winner=null推出完整字交集空。官方calls只指wrapper，303283=71610+231672+1；不含回归/join/CLI内部。

## 提交及完整官方CLI
round3-app-bridge03-submission.txt(.tex)是与task原TXT相同SHA的完整当前四行；round3-app-bridge03-candidate.json(.tex)是当前完整sac-07445候选；round3-app-bridge03-cli.json(.tex)收齐returncode/stdout/stderr，read-back核SHA与原task一致。
实际命令由封存源执行：python -B -m verifier --manifest /output/round3-fixed/official/competition/tools/verifier/data/manifest.json --submission /output/round3-submission.txt --pretty。
官方commit a0fd6e6f52d82c93ccc06ab91d81e8fa3678256e，恢复archive c8ed06893cf895f1221cae149de5b1c4af1657f713aeaf225618723ced9960d6，41文件锁hash；stable_core SHA234b164c766bf7fd2e1bee7f7bfb3910319c5885e4250bf56520d2d2b0f46e9d。acceptance保留external_preflight/native_receipt=false标签；真正原生执行task证据单列，不改外部工程来源。CLI全accepted仅证明提交格式/整路径中间态、资源及终点合法；不证明15最优或排行榜。

## 数学发布、采用、失败及公开入口
结果新版本M-6a8ed93c5a757eba@1；原预注册M-c6b311ca449ce973@1、解析M-02edaae37c383f5e@1；目标归约M-95d49b3f9570d1f2@1既有read/adopt1342/review1394记录，不倒填新依赖。没有采用其他方向新定理，也没有把自身结果当独立review。
旧门禁M-484776873908098a@1与M-4ece2fa2f8e1b6ab@1不改；新USER修复后root用明确新ID一次执行，不重放旧unknown。Stable08491外部完整补核与原生未完成复核分列。
round3-app-bridge03-public.zh.md供lain-s-note中文补充，本索引供yohaku；本地待审无公开URL。无平台上传或排行榜请求。完成本小边界后research_finish，不续题、不等另一模型。
