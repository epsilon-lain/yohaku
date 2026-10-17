# Loom 0.1.4

Yohaku 的文本宏转换工具。人和具备程序调用能力的 AI 使用同一个入口：传入源文档路径，Loom 读取它指定的宏，并按规则生成文件。转换过程不调用模型、不联网、不启动生成程序。

本版已在 Linux x86_64 环境实际验证；Windows 用户可在 WSL 中使用。包内有源码、离线依赖、可执行程序、八份旧格式源文档，以及一份供逆向测试的外来 Python 文本。初始不包含 Loom 生成的示例产物。

## 从已有文本逆向得到 tex

```sh
./loom reverse examples/incoming/demo.py
```

读取原文件，在旁边创建 `demo.py.tex`。不会修改原文件，不会运行 Python，不调用 AI。新 tex 使用 `yohaku/0.2`，包含原文、实际输出地址与导入时的路径/字节数/SHA-256；**没有 AI 笔记，没有 links 关联字段**。笔记与关系可以由人或 AI 后续明确补充。

```sh
./loom inspect examples/incoming/demo.py.tex --json
./loom sync examples/incoming/demo.py.tex
python3 examples/incoming/demo.py
```

这条链是已有文件 → tex → 原样生成。支持所有 UTF-8 文本扩展名，包含 Python、Rust、JSON、HTML、Markdown、配置、自定义文本等。空文件、BOM、CR/LF/CRLF、正文围栏、最后一行没有换行都保持字节一致。当前不进行非 UTF-8 编码转码。

已存在的目标 tex 不会被覆盖；如果生成文件已经归属于另一份 tex，reverse 不会抢占它。查看已有来源或为导入指定不同的输出地址。

将外部原文件与生成副本分开时，可以明确指定：

```sh
./loom reverse examples/incoming/demo.py \
  --source world/imports/demo.py.tex --root . --output generated/demo.py
./loom sync world/imports/demo.py.tex --root .
```

这里 `.tex` 放在项目内，生成副本写到 `generated/demo.py`，原文件保持独立。`--source` 路径相对于当前工作目录，`--output` 相对于生成根；不指定 `--root` 时仍以 tex 所在目录为根，根目录需要已经存在。自定义子目录可以在显式根目录下创建。

reverse 自身只创建 tex 和必要的原样宏；从第一次 build/sync/watch 开始登记生成物归属。之后继续使用旧有同步、删除流程。默认 output 指向原文件，因此调用 sync 后，它会成为该 tex 的追踪产物；想保持外部工具文件独立，就使用不同的 `--output`。

根目录缺少 `macros/raw.source.md` 时，会创建一个不带笔记的固定 emit 宏。已有宏只验证和复用，不改写。导入不会推断源语言或程序用途，target 为 text。

给 AI/程序使用同一入口：

```sh
./loom reverse FILE --json
./loom inspect FILE.tex --json
```

reverse 结果包含 input、source、root、output、macro_path、input_hash、bytes_read、created_macro。inspect 直接返回解析后的原文、正文、头部、输出元数据、笔记映射和 UTF-8 正文字节范围；缺失笔记表示为 `{}`。JSON 源映射的 source_version_declared 在没有笔记时为 null。

## 先在本地试一次

解压到新的文件夹，进入里面的 loom 目录。在 WSL 终端执行：

~~~bash
chmod +x loom bin/loom-linux-x86_64
./loom examples/lain_baka.txt
~~~

最初只有 examples/lain_baka.txt。命令执行后，在同目录新增 examples/lain_baka.py，原文档保留不变。示例正文是：

~~~python
print("`lain baka`  ")
~~~

其中反引号和两个空格按字面保留。若要执行产物，另外运行：

~~~bash
python3 examples/lain_baka.py
~~~

简短的本地测试步骤见 TEST_LOCAL.md。

## 一个路径就够了

可以把完整文件路径直接交给 Loom。调用时的当前工作目录不会决定生成位置：

~~~bash
/完整路径/loom/loom "/完整路径/世界文件夹/文档.txt"
~~~

默认基准是源文档实际所在的文件夹；符号链接会解析到实际文档。宏引用和 output 都相对于这个基准。默认示例写 output: lain_baka.py，因此产物与文档相邻。

也保留原来的调用形式：

~~~bash
./loom build examples/lain_baka.txt
./loom build examples/lain_baka.txt --root examples
~~~

--root 可覆盖基准，用于多个源文档共用同一个世界根目录的情况。直接调用 bin/loom-linux-x86_64 与调用顶层 loom 启动脚本等价；顶层脚本需要与 bin/ 一起保留。

## 给 AI 和其他程序调用

加 --json，成功或失败都只在 stdout 写出一份 JSON；退出码仍表示执行结果：

~~~bash
./loom examples/lain_baka.txt --json
~~~

成功包含 format: loom-result/0.1、ok: true、action: build，以及 result 中的 source、output、map_path、build_id、bytes_written。

失败包含 ok: false 和 error。转换错误有 file、line、message 和 exit_code: 1；参数错误的 kind 为 usage，exit_code 为 2。JSON 模式下不再向 stderr 重复打印同一错误。普通模式的错误仍写 stderr。

JSON 标志可以放在命令前或文档后。文件名以连字符开头时，用 -- 将它与选项区分：

~~~bash
./loom --json -- "-文档.txt"
~~~

右键入口以后可以把选中的文件路径交给这个相同入口。本版交付终端入口与 Rust 库，没有注册 Windows 右键菜单，也没有加入 AI 服务。

## 修改源文档

编辑源文档正文，保存后再次调用 Loom，更新对应产物。生成位置由 output 指定，target 与代码块类型用于描述。正文的字符、缩进、空行和 CR/LF/CRLF 均保持原样；Loom 不翻译目标语言、不修复语法或插入 import。

AI 笔记如果存在，就作为资料保留在源文档中，Loom 只检查其结构，不修改或认证它。旧 yohaku/0.1 仍要求笔记；新 yohaku/0.2 允许没有笔记，不填写伪造作者、说明或版本。

## 源文档与产物一起存在

0.1.2 新增同步入口。保持下面的命令运行，在编辑器或 Windows 文件管理器中修改、删除同一份源文档：

~~~bash
./loom watch examples/lain_baka.txt
~~~

源文档保存后自动生成；源文档消失并持续约一秒后，删除它生成的文件和对应映射。监视持续到 Ctrl+C，源文档恢复后会再次生成。同一个进程也会观察被选中宏的修改。

同步时只保留当前版本的映射。修改 output 后，新位置生成成功才清理旧产物；源文档仍存在但格式错误、宏缺失或宏命令错误时，保留上次产物。

不用持续监视时，可以进行一次同步。即使源文档已经删除，仍传入原来的路径：

~~~bash
./loom sync examples/lain_baka.txt
./loom sync examples/lain_baka.txt --json
~~~

源文件存在就生成并清理旧版本；源文件缺失就从记录清理对应产物。因此停止监视期间删除的源文件，可在重启后用 sync 补清理。使用过 --root 时，后续 sync/watch 也应使用相同的 --root。

每次普通生成也登记来源与产物。记录放在基准目录的 .loom/records/，归属标记放在产物目录的 .loom/owners/；没有登记的文件不按名称猜测删除。普通 build 保留历史映射，sync/watch 则会收敛为当前映射。清理后仍可留下用于复用的空目录和零字节锁文件。

已经被手动修改的产物或映射会保留，并显示 retained；单次 sync 的退出码为 1。后续可自行处理该文件，或恢复生成时的内容再调用 sync。不同源文档不能同时认领同一个产物地址。输出地址不能放在保留的 .loom 元数据目录里。

--json 对 sync 返回一份 JSON，result 中有 source、state、build、removed、retained；state 为 generated、removed、absent 或 retained。watch 返回逐行 JSON 事件，先给出 action: watch，后续事件与单次 sync 的结果相同。解析错误仍使用 error 字段；监视过程中出现错误不会结束进程。

本版监视一个指定路径，没有注册系统后台服务。停止 watch 后不会自动响应删除。重命名或移动源文档会视为旧路径消失；新路径需另行调用。请保留 .loom 记录；如果连基准目录和记录一同移除，就无法在重启后根据它恢复外部输出的归属。v0.1.1 产物需在源文档仍存在时用新版生成一次才能登记，旧版历史映射不自动导入。

## 同一宏，多种文本文件

| 源文档 | 输出（相对于文档目录） | 内容 |
| --- | --- | --- |
| examples/lain_baka.txt | lain_baka.py | Python |
| examples/hello_rust.source.md | generated/hello.rs | Rust |
| examples/page.source.md | generated/page.html | HTML |
| examples/config.source.md | generated/config.json | JSON |
| examples/readme.source.md | generated/README.md | Markdown |
| examples/message.source.md | generated/message.txt | 纯文本 |
| examples/custom.source.md | generated/world.custom | 自定义文本 |

所有示例共用 macros/raw.source.md 中的命令：

~~~text
<%* emit(body, output) %>
~~~

本版支持一个原样输出命令，且没有输出扩展名白名单。程序写出已有的 UTF-8 文本；图片、视频、其他二进制编码和完整脚本语言不在本版中。

## 失败保护与源位置

Loom 完成解析和宏验证后才写临时文件。产物、映射、归属记录都先准备临时文件；解析、宏验证、临时写入或映射保存失败时保留旧产物。先发布映射，再替换产物，最后发布归属记录。每次映射存储源文件与宏快照、摘要、正文位置和行号。

用转换时显示的映射地址查询产物行号：

~~~bash
./loom map PATH_TO_MAP.json 2
./loom map PATH_TO_MAP.json 2 --json
~~~

当前源文档改变时显示保存的快照；产物与映射摘要不符时拒绝定位。程序不自动解析每种语言的异常输出。故意除零的 examples/runtime_error.source.md 可用于测试这一过程。

映射、产物和记录不是一次原子操作；中途终止或记录发布失败可能留下尚未登记的产物或未使用的映射。正常错误返回时清理临时文件，强制终止可能留下临时文件。相同 root 的操作使用系统文件锁串行，进程退出后释放；本版不承诺断电持久性，或多个不同 root 并发写入同一地址时的事务性。

## 从源码构建与接入

在本目录使用 Rust / Cargo 1.75 或以上：

~~~bash
cargo build --release --locked --offline
cargo fmt --check
cargo test --locked --offline
cargo clippy --locked --offline --all-targets -- -D warnings
~~~

依赖来自包内 vendor/，详见 VENDOR.md。本配置已在 Linux 验证，未验证 Windows 原生编译。

Rust 库 crate 名为 loom。单文档入口会使用文档所在目录：

~~~rust
let result = loom::build_document("examples/lain_baka.txt")?;
~~~

需要指定世界根目录时使用 loom::build(source, root)。sync_document(source) 和 sync_with_root(source, root) 执行一次同步；Watcher::new(source, root) 创建监视状态，宿主定时调用 poll() 即可共用同一套行为。reverse_file(input, source, root, output) 导入已有 UTF-8 文件，后三项为可选路径；parse_file 读取完整源文档，map_line 查询经过校验的快照位置。终端、未来的右键入口和宿主程序可以共用这些实现。

格式详情见 FORMAT.md，实际检查记录见 VERIFICATION.md。

