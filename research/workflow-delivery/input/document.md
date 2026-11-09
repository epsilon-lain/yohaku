# Yohaku 内部开发 0.1.9.8

0.1.9.1 修复从旧工程升级后 Develop 提示缺少 update_manifest.json 的问题。安装时一并校验、备份和更新安装脚本与清单；原有世界和配置继续保留。此前只在完整解压目录验证开发准备，本次补充从真实升级目录运行 Develop 的回归验证。

目标是从 Yohaku 内的智能体开始建设 Yohaku default。Socius 使用现有模型连接；源码、生成文件、编译产物和运行日志留在开发世界。当前宿主版本保留，候选版单独验证。

## 首次使用

1. 更新并启动后，进入 Techne。先停止正在运行的工具、结束 AI 回合，再点 **Develop**。
2. 按当前工程源码准备独立副本，文本文件通过实际 Loom reverse 注册为 .tex；原目录结构和脚本执行位保留。原宿主源码、用户 worlds、模型身份和 Key 不被复制成候选数据。若开发副本已存在，重新准备不会覆盖其中的修改。
3. 准备完成后清单出现四项：Yohaku check、Yohaku core tests、Yohaku build candidate、Yohaku preview candidate。首次操作还不执行编译。
4. 到 Socius 连接原来的模型，确认 Read / Write / Run 已开启；打开任意页面的 Chat，粘贴下面的第一个任务。

> 读取 memory/yohaku-development.md 和 memory/development.json。我们开始开发 Yohaku default。先读取 files/yohaku-default/config/shell.json.tex，把默认标题改成 Yohaku shared workspace，保留其他设置和笔记。同步后运行 yohaku-check，等待结束，读取实际退出码与日志。失败就根据错误修复并重试；完成后告诉我修改文件和检查结果，不要声称当前宿主界面已经更新。

这一步验证实际文件编辑与检查。检查通过后再说：

> 构建刚才修改后的候选版，等待 yohaku-build 完成并检查退出码；成功后打开 yohaku-preview。不要替换当前版本或发布任何内容。

## 源码与工具

- 工程根：`files/yohaku-default/`。
- tex 是导入源码的编辑入口。源文件登记在当前世界的工作区索引中，AI 的 revision 检查、Loom 保存与自动同步共用原有流程。
- 新建嵌套文件时先 write_text，再 adopt_file；后续修改对应 tex。不将二进制当成可逆文本。
- 开发记录：`memory/development.json`；说明：`memory/yohaku-development.md`。适合把事实性的设计决定写进 memory，保留后续工作的起点。
- 构建输出：`tools/state/yohaku-development/target/`。`yohaku-build` 同时更新副本中的 Rust 工作区 CLI，使候选 Python 桥接与源码一致。
- 日志：每次 run_tool 返回的 `log_path`，位于 `tools/logs/`，read_text 可读取；超过 2 MiB 时保留尾部。
- `run_tool(id, wait:true)` / `tool_status(wait:true)` 一次等待最多 30 秒，内部轮询不消耗新模型轮次；仍 running 时继续等待。每个编译/测试子命令最多 900 秒，超时停止其进程组。两项 Cargo 并行编译任务；未声称聚合内存硬限制。

## 本地依赖和范围

Develop 从已有 rustc 查询完整 sysroot，并找到现有 Cargo registry 的 src/cache/index，只读接到固定运行时路径。Rust 与依赖不会重复下载。路径记录在宿主 Yohaku 的 `config/development-runtime.json`，该文件不进入开发副本和发布包；普通世界文件工具不能修改宿主记录。

源码执行继续要求 bubblewrap 的真实隔离预检查。模型调用在 Socius；工具内无模型 Key、宿主 Home、Windows 盘或宿主网络。编译产物和新缓存写在世界里。没有隔离成功的回退启动。

缺少编译器/缓存时，准备会报告具体错误。工具离线且使用 --locked，不自动获取新依赖；本机先成功编译一次当前安装的 Yohaku，再准备开发，可建立已有依赖缓存。后续添加新依赖需单独设计或由人准备。

`yohaku-test` 执行库/工作区集成测试、工具窗口逻辑与配对流 Wayland 协议测试。它不等于完整 UI、HTTP mock 或真实图形桌面验收；`yohaku-check` 编译所有 target。编译系统会执行项目构建脚本，因此所有动作都在工具隔离内执行。

预览候选版使用自己的空白世界；仅此子世界的跟踪元数据可由候选 Yohaku 写入，外层开发世界的 .yohaku/.loom 仍只读保护。预览不复用父 Socius 的 Key。与当前最小 Wayland compositor 的实际 EGL/图形兼容性仍需本地验收；失败要读取日志，不代表源码构建已经失败。

当前没有自动替换宿主、自动导出发布包、上传 GitHub/Steam，或 Claude Code 订阅登录。本版新增实验性 Windows Codex 桥接，见 README_WINDOWS_TOOLS.md。先让内部智能体完成一次源码改动与真实构建，再继续做这些接入。


## 更新部署时的 IME 回归检查（2026-10-20）

构建成功、XIM selection 存在或主窗口可见，都不能证明中文候选可见。已有修复必须保留：Fcitx 无 -k 的独立生命周期、XIM refocus、宿主与嵌套 IME 转发及各自输出路由。不要为了构建更新覆盖现有依赖缓存修复。

`yohaku-build` 在 Cargo 成功后、安装候选 CLI 前运行只读 `agent/yohaku_ime_check.py`，核对 IME 源/.tex 一致、已有转发和二进制 refocus 标记；失败返回非零，不继续宣布构建部署通过。这个检查在现有构建沙箱内不访问宿主 Fcitx、总线或显示，未扩大世界权限。

宿主部署前保存当前进程版本、配置和故障日志；不要先重启服务。宿主部署后的人工操作期间，在普通 Linux 控制器执行（PID 与日志换成实际值）：

```bash
python3 -B agent/yohaku_ime_check.py --project . --binary target/debug/examples/yohaku_compositor --runtime-pid 12345 --event-log diagnostics/ime-current-launch.log --watch-seconds 30 --manual-record diagnostics/ime-manual.json --output diagnostics/ime-deployment-check.json
```

此命令只读，绝不启动模型、重启 Fcitx/宿主或自动修复挂载。它核对宿主与实际总线服务的 DISPLAY/总线、XIM selection、全新 XOpenIM、实际 /proc/exe 哈希，以及观察期间**新增**的 WSLg 图像分配错误；不会拿历史错误当新故障。需要先保留原命令 `./run-yohaku` 的启动日志，未记录时不能补造历史 Preedit/Commit；输出只统计事件类型/字符数，不导出草稿。非空 Preedit 未观察到就记未知，不能从候选可见反推。

人工记录 JSON 的 `first_launch` 与 `after_restart` 各包含 `chat`、`techne_codex`；每项明确记录 `candidate_visible`、`chinese_committed`、`no_duplicate` 三个布尔值，必须来自人的实际确认，不自动填写 true。步骤：以原 `./run-yohaku` 启动，分别在内置 Chat、Techne Codex 选词并用空格上屏；不点 Send。保存草稿后正常关闭，再以同一原命令启动并重复两入口测试。不要为输入验收发模型请求。

源与自动检查通过仅表示自动部分通过；`fully_accepted` 还要求真实运行检查与两阶段两入口人工确认。运行检查缺人工项时退出2，清晰标待验收，不视为已部署合格。若候选窗口在 X11 映射、中文能上屏，但 Windows 候选不可见且 Weston 持续 rdp_allocate_shared_memory EIO，应排查 WSLg 图像通道；不要据此盲目重启 Fcitx或回滚终端功能。挂载恢复属于人工诊断，不加入应用启动自动重试。完整现场与本轮结论见 diagnostics/ime-chat-20261020/RESULTS.md。
