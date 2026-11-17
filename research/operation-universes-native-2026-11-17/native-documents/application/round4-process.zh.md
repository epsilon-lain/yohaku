# round4应用过程索引

USER2411；Sol/max600秒64工具，沿原截止/总turn，不新增或wake模型，不research_continue。先权威记忆@c5bfa80650945ae8cdfa3df081689edda2fe13f2e22c86d45c953c87730ef534/resources/math索引，再读resources@1、seed@1及PANO38/39/40。阅读元数据及本人的概述保存round4-literature-reading.zh.md；原文私有，不在manifest sources中。seed采用event2882；页38/39/40阅读启发采用events2893/2895/2897，未把IUT当计算前提。

新方法自主选择、群seq75预报；代码/协议先冻结并发表M-1729534495821452@1。只追加round4源/action，旧源/任务/失败不改。manifest revision CAS caad0d356303bc41ffc30986442c4ff98b814b92095d270fcc99135502d0b5d6；新action round4-window-search。真实task project-task-5c6ffec803aad5ea7d4621ee34ecfeeb，request app-r4-07445-guarded-window-v1，source_set 00f15223d9906cb64ab18e730709c7e13c5c6b99f680ceec687849cd9c2a93ee。程序只执行本新实验，没有重跑round3。

源映射：
[
  {
    "body_source_line": 10,
    "macro": "macros/raw.source.md",
    "macro_hash": "67ececca3997f000b8d50523fa3bb68af48f319b039493b87d0ce30414cb3bd8",
    "map": ".provenance/maps/7acf92b0aedd1b57c9e5a75b229c95cbddf98ffc93a9f5fea16b08e5189f047f.json",
    "output": "round4-protocol.json",
    "output_hash": "80f6bc4f5c06cc9a4076fe103cc9c7b1d1a1e55f321119f8a78b509404812a46",
    "source": "files/application/round4-protocol.json.tex",
    "source_revision": "d2b2554a56d7eab4559b91dfdb8dfaecb394299ed01a43513eb77ca576c21551",
    "generated_line_count": 48
  },
  {
    "body_source_line": 10,
    "macro": "macros/raw.source.md",
    "macro_hash": "67ececca3997f000b8d50523fa3bb68af48f319b039493b87d0ce30414cb3bd8",
    "map": ".provenance/maps/775c76f8ca2111448311d0ae60f0b05ef4e4488ba42f13f7fec7f78a0d568736.json",
    "output": "round4-window-search.py",
    "output_hash": "7b566c75cba2e814c89fd142e5733f6047496b85389a74847c4b16a2f5d4517d",
    "source": "files/application/round4-window-search.py.tex",
    "source_revision": "9245544b39507cb48430c9f2e53877c96ff4c9e371bb7975a563c73858be382c",
    "generated_line_count": 110
  }
]

原产物：
round4-results.json 21374 bytes SHA256 59e9f7db0fccc4ddf30aff4b1c35ac2d944d17255328bea2c38532934d1be652
round4-checkpoint.json 11911 bytes SHA256 8c597baa22ef74db892dcd4018dda3ea70118edda19a187364fab37566e97f78
round4-candidate.json 177 bytes SHA256 5c0aa86250d7e42aeb7e50d62c171233ded1b798ee3ca619c0512c0a0214341c
round4-submission.txt 196 bytes SHA256 f82d435bd4cde897fed72f188b2f241b79e93dafd3871c47d1c81828b87738dc
round4-cli.json 1004 bytes SHA256 8e1eff012c17f016781d2933a5291839d65193823fc0a315deb9ed0c1eee2d54

round4-evidence.json保存结果/精确转换证书/原产物hash和完整CLI读取值，不冒称原results全文副本或独立复算。stdout1971bytes、stderr0已按字节读完；原watch wait_ms10000被参数限制拒绝，随后只查同task已done，不重启。14入口全完成、60窗口0命中、无guard；范围仅rank3/radius3局部固定窗口。51,301计数仅搜索wrapper，不含恢复/回归/证书回放/acceptance/CLI内部；没有beam，故无beam丢弃数据，不套用上一轮136958。

round4-cli-local.json收齐原CLI rc/stdout/stderr，完整857字符stdout；round4-submission-local.txt为本轮CLI对应的重新排序15步四行，hash须同原f82d435bd4cde897fed72f188b2f241b79e93dafd3871c47d1c81828b87738dc。旧优先基线保留files/application/round2-submission-local.txt（旧15/work128），本轮新15/work130合法但更差，不取代其最优性/优先声明。整路径官方检查中间态/资源/终点与提交格式；acceptance工程仍external_seed，本机task凭据另列。平台上传/排行榜均未授权未做。

中文round4-public.zh.md供lain-s-note；此过程索引供yohaku，仅本地待审。新结果M-c772d35d33d375d7@1，未独立核验；新证明是初等群字恒等式，不宣称文献优先权。旧Stable08491随后外部复核与原生失败保持分列。完成小交付即finish，不等待他人。
