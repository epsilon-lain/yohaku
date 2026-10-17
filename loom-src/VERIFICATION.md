# Loom 0.1.4 实际验证

基于本次上传的 Loom 0.1.2，增加 reverse、inspect、可选笔记的 yohaku/0.2 格式与精确文件末尾支持。既有 yohaku/0.1 的解析、生成、同步、监视和清理约定保留。

验证环境：Linux x86_64、Rust/Cargo 1.75，使用包内离线依赖。日期：2026-10-13。没有在 lain 的实际 WSL 机器执行；包内 TEST_LOCAL.md 提供实机步骤。

## 已通过的检查

- 旧转换/解析测试：28 项。
- 旧同步/删除测试：16 项。
- 新逆向测试：23 项。合计 67 项，失败 0 项。
- cargo fmt --check、cargo clippy --locked --offline --all-targets -- -D warnings。
- cargo build --release --locked --offline；发行二进制显示 loom 0.1.4。
- 打包后从无生成物副本执行真实启动脚本：reverse → inspect → sync → Python 运行 → 删除 tex → sync 清理。
- ZIP CRC、源代码、离线依赖配置和二进制 SHA-256 检查；包内没有生成产物、来源归属记录、编译 target 或临时文件。

## 逆向覆盖

Python、Rust、JSON、HTML、Markdown、Shell、CSV、TOML、YAML、自定义扩展名与普通文本；同一转换逻辑不限制扩展名。

空内容、Unicode、UTF-8 BOM、NUL、CR/LF/CRLF、混合换行、文件末尾没有换行、正文中的围栏/区块标题/宏文字、带空格/引号/换行与 Unicode 分隔符的文件名。

明确验证 reverse 不执行正文、不修改输入、不填笔记或关联、不覆盖已有 tex、不改写已有宏、不抢占其它来源的产物。两个逆向进程同时导入同一文件时只允许一份新 tex 成功发布。

新 tex 可以继续使用原来的 sync/watch 修改与删除流程。生成的映射保留实际正文字节范围，无笔记时版本字段为 null；补充有效笔记后为其声明的正整数。

## 范围

当前 forward / reverse 处理 UTF-8 文本，不做编码转码，不对程序做语义翻译。reverse 是提取原文与确定的导入事实，理解和关系由人/AI 后续补充。

reverse 默认的输出地址是原文件；只有后续 build/sync/watch 才登记产物。指定独立 --output 可以保持外部原文件与生成副本分离。现有笔记与来源不会被逆向自动覆盖。

yohaku/0.2 需要新版 Loom，旧版将明确拒绝该格式。历史来源图的数字版本仍可由新版 map 读取。

仍然没有后台系统服务；watch 需要保持运行。普通文件错误、宏错误及手动修改过的产物沿用旧版处理规则。零字节锁文件或可复用空目录可以留下。

发行二进制摘要见 BUILD_INFO.json。测试源码位于 tests/，可在本项目根目录用 cargo test --locked --offline 重复执行。
