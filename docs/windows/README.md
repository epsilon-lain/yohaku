# Windows 下载与试用

原生 Windows x64 便携技术预览版 **2026.11.17-preview1** 已发布。

[下载可运行 ZIP](https://github.com/epsilon-lain/yohaku/releases/download/v2026.11.17-preview1/Yohaku-2026.11.17-preview1-windows-x64.zip) · [Release 说明与 SHA256SUMS](https://github.com/epsilon-lain/yohaku/releases/tag/v2026.11.17-preview1)

## 使用

1. 下载 `Yohaku-2026.11.17-preview1-windows-x64.zip` 并完整解压到有写入权限的本地目录。
2. 双击 `Launch-Yohaku.cmd`。无需安装 Rust、Python 或 WSL；保留所有包内文件。
3. 可使用原生窗口、本地文档/Loom 和 Socius 设置。模型连接由你自行配置，首次启动不请求模型或登录账号。
4. 默认资料、配置、聊天和诊断位于解压目录内 `data/Yohaku`，默认世界为 `data/Yohaku/world`。启动日志在 `logs/last-launch.log`。

GitHub 的 `Source code (zip)`、`Source code (tar.gz)` 和 Code → Download ZIP 是仓库源码，不是可运行的 Windows 包。此仓库标签标识发布工具；实际 Windows 源快照、基线和二进制哈希由附件及包内 `BUILD-SOURCE.json` 记录。运行包只带运行所需的 Python 源与宏，不把仓库源码 ZIP 宣称为完整的原生 Windows 源快照。

## 已验证范围

Windows 11 Home x64（build 26300），全新数据/Profile 环境变量、仅系统 PATH，已验证原生启动、普通及中文/空格/感叹号路径、文档经包内 Loom 创建、关闭重开保持资料、整包移动后的默认数据位置、缺少运行文件时的具体错误日志与非零退出码，以及解压包的 Enter/多行离线回环。

**仅在当前电脑隔离环境验证，尚未在独立干净 Windows 环境验证。** 这不是另一台电脑、另一个 Windows 账号或虚拟机的验收。真人输入结果和精确 ZIP 哈希以该版 Release 的验证记录为准。

真实模型工具调用、图片理解、外部 Codex 登录/沙箱、Developer 自举构建和浏览器/研究生态继续暂缓。其他输入法、物理长按和极长路径没有新增兼容性保证。预览未数字签名；系统提示时自行判断，本项目不要求关闭系统保护。

## 升级、移除与反馈

升级先解压到新目录，保留旧目录和资料；可用 Open workspace 主动打开旧世界，或关闭应用后复制自己的 data。主动选择的外部世界仍使用原位置。移除解压目录会同时移除其中的 data，先备份自己的资料。

请在 [Issues](https://github.com/epsilon-lain/yohaku/issues) 提供版本号、Windows 版本、复现步骤及相关日志文字。日志可能包含本机路径和任务内容，分享前检查，只提交需要的部分。

维护者流程见 [发布步骤](RELEASING.md)。本版是 technical preview / prerelease，下载链接指向精确版本，不使用 /releases/latest。
