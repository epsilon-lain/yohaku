# Loom 0.1.4 本地测试

进入新包里的 loom 文件夹，在 WSL 中先执行：

```sh
chmod +x loom bin/loom-linux-x86_64
./loom --version
./loom reverse examples/incoming/demo.py
```

应显示 loom 0.1.4，并在 incoming 文件夹出现 demo.py.tex。查看这份 tex：有原正文、输出地址和导入事实，没有 AI 笔记或 links 关联。逆向没有修改原 demo.py。

验证重新生成是否逐字节相同：

```sh
cp examples/incoming/demo.py /tmp/loom-demo-original.py
./loom sync examples/incoming/demo.py.tex
cmp /tmp/loom-demo-original.py examples/incoming/demo.py
python3 examples/incoming/demo.py
```

cmp 没有输出且成功退出，表示内容相同。Python 应打印 lain kawaii。这个原文件故意没有末尾换行，新 tex 会通过 body_separator 保留这一事实。

继续验证编辑与删除：

```sh
./loom watch examples/incoming/demo.py.tex
```

保持运行，用 VS Code 修改 tex 正文，再运行 Python 看结果。删除 demo.py.tex，约一秒后 demo.py 与对应生成映射应清理。测试结束按 Ctrl+C。

再次 reverse 同一文件时，已存在的 tex 不会被覆盖。使用新的文件、明确指定不同的 --source/--output，或者直接编辑已有 tex。

下面保留原有正向与清理测试说明。

## 原有文档的本地同步测试

把新版解压到一个新文件夹。进入 Loom_v0.1.4/loom 文件夹后打开终端、输入 wsl。以下命令都在里面的 WSL 终端运行，不是在外层 Loom_v0.1.4。

## 1. 启动监视

先复制一份示例备份，再开始监视原文档：

~~~bash
chmod +x loom bin/loom-linux-x86_64
cp examples/lain_baka.txt examples/lain_baka.backup.txt
./loom watch examples/lain_baka.txt
~~~

终端显示 watching、generated 和 map，此时 examples/lain_baka.py 出现在源文件旁边。保持这个终端运行；执行完其他测试后用 Ctrl+C 停止。

## 2. 修改与删除

在 Windows 中打开 examples/lain_baka.txt，只把「正文」里的整行改成 print("lain kawaii")，保存。约半秒后产物更新。另开一个 WSL 终端，进入同一 loom 文件夹，运行：

~~~bash
python3 examples/lain_baka.py
~~~

输出应为 lain kawaii。

现在从 Windows 的 examples 文件夹删除 lain_baka.txt。约一秒后 lain_baka.py 也消失，终端显示 removed；对应映射同样被清理。

在第二个 WSL 终端恢复原文档：

~~~bash
cp examples/lain_baka.backup.txt examples/lain_baka.txt
~~~

watch 仍运行时，.py 会重新出现。备份只是用于恢复这份测试文档，没有被交给 watch。

## 3. 停止期间删除，重启后补清理

在监视终端按 Ctrl+C。第二个终端执行：

~~~bash
rm examples/lain_baka.txt
./loom sync examples/lain_baka.txt
~~~

即使 .txt 已经不存在，sync 也能按原路径清理之前登记的 .py 和映射。结束后恢复示例：

~~~bash
cp examples/lain_baka.backup.txt examples/lain_baka.txt
./loom sync examples/lain_baka.txt
~~~

## 4. 给 AI 的结果

~~~bash
./loom sync examples/lain_baka.txt --json
~~~

单次 sync 输出一个 JSON。watch 加 --json 则逐行输出事件，可持续读取。只要保留新版生成的 .loom 记录，同步就不依赖一直运行的同一个进程。

watch 期间源文档格式错误或宏缺失会保留上次产物。生成文件被手动改过时，删除清理会显示 retained 并保留该文件。

本版没有系统后台服务；自动同步需要 watch 正在运行。没有接入 AI 笔记刷新，也没有注册 Windows 右键菜单。
