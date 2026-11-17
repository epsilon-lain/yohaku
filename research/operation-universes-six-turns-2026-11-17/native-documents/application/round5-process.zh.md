# round5过程包索引（event2974）
## 用户目标与自主选择分开
USER要求新独立阶段诚实接续未证最短的实例、原始步评分、完整官方回执及保留失败。作者自主选择“中间态资源单调相邻交换+精确二步环删除”这一小变换类；理由是round4已有精确同端点却work128→130的反例，须先补可保资源条件再测试能否露出可消片段。不是用户预设必须算、必须改善或旧搜索重复。
## 预执行冻结
- 群选择报告seq82（wake=[]）；没有新增/wake其他模型。
- 权威记忆与resources已实际读；先math_search 07445与resource索引，再精确读M-c772d35d33d375d7@1、M-1729534495821452@1、M-5606eba96406db45@1。
- 上述阅读与对M-c772d35d33d375d7、M-5606eba96406db45的采用、独立复核分别留证：采用事件3478/3480仅作者声明；本轮无独立复核。M-1729534495821452旧程序只作边界定位，未运行。
- 新文件round5-protocol.json.tex、round5-diamond-search.py.tex；版本/生成hash见round5-freeze.json.tex。首次写后做了一次提交前计时修正，将summary搜索时间截在CLI前；冻源/发表/执行之前完成，不是看结果调参。
- Manifest只追加这两新源和round5-diamond-search action，旧源/actions保持。文献全文不在计算snapshot。预检missing=[]。
- 冻结源码/证明公开到共同库M-c398c4f1100cb45e@1后单次task_submit，没有重试/重放。
## 实际执行与全程证据
request app-r5-07445-monotone-diamond-v1
task project-task-c0f44bc9f068248f856aa641a7c3aac4
source_set/snapshot fa80ff558a1cbf299854a57601d3fb42ed0e83321606a2385de1f6e94c3512b1
exit0、cleanup_confirmed、output_complete、stderr0；六原产物都通过provenance hash核验。
{
  "paths_discovered": 2,
  "processed_paths": 2,
  "queue_pending": 0,
  "closure_complete": true,
  "guard": null,
  "baseline_signature": {
    "length": 15,
    "peak_total_relator_length": 13,
    "work": 128
  },
  "current_signature": {
    "length": 15,
    "peak_total_relator_length": 13,
    "work": 128
  },
  "current_path": [
    6,
    4,
    12,
    1,
    3,
    6,
    12,
    2,
    5,
    6,
    4,
    2,
    4,
    16,
    15
  ],
  "strict_primitive_improvement": false,
  "best_node": 0,
  "search_elapsed_seconds": 0.0008496290029142983,
  "counts": {
    "positions_checked": 28,
    "swap_attempts": 28,
    "swap_first_illegal": 2,
    "swap_second_illegal": 2,
    "unequal_exit": 20,
    "cost_increasing": 2,
    "endpoint_equal_swaps": 4,
    "resource_monotone_swaps": 2,
    "cycle_deletions": 0,
    "duplicate_paths": 1,
    "official_rejections": 0,
    "official_candidate_verifications": 1,
    "search_apply_calls": 32,
    "apply_cache_hits": 22,
    "processed_paths": 2
  },
  "platform_upload": false
}
包装apply计数排除恢复、基线回放、official.verify内部及CLI；22缓存命中另列。单次极小计时不代表搜索收益。
## 读回与交付
实际按指针读summary、challenge、全部16个current_trace状态、stable_resource_source_lines、acceptance两页、证书/1、CLI完整stdout。没有声称整个13623字节result全文无遗漏读取；原始所有产物均保留。
当前A的全CLI四行accepted；新增等cost B另有整条official.verify但未单独CLI，此与最终候选验收分开。
round5-evidence.json.tex含摘要、两步证书、验收、实际16态及原产物hash。
round5-cli-local.json.tex保完整CLI returncode/stdout/stderr，round5-submission-local.txt.tex为本地提交源；不上传/查榜。
科学中文稿round5-public.zh.md.tex供lain-s-note；过程/源码/证据索引供yohaku，宿主尚未给公开URL。
## 小失败/限制
task_result_index(limit=10)返回Invalid value for limit，仅展示调用失败，未重新提交计算；改为已知产物精确指针读。无计算guard/截断/beam丢弃。闭包无短路是有限方法类结论，不是Stable全局下界。
旧门禁/stop/超时/外部08491复核与本机失败历史保持原记录。外部official与acceptance身份不改，acceptance输出native_receipt=false不抹去，真实原生task回执另记。
## 通信帮助与文献
本任务冻结方法前未采用新同伴消息；采用旧共享资源签名公式及旧应用反例。结果群报告seq87（wake=[]），不等待同伴，也无新独立review。旧PANO38/39/40阅读不冒本轮新读；本轮未用IUT定理、未公开整页/PDF/私有记忆。
## 开放问题（没有自动续题）
暂增work而后下降的合法转换链是否可通向少于15步？当前单调闭包结论不覆盖。尚无必要新任务被排队；本轮小交付后finish，不为耗尽额度再搜索。
