# Loom 外层格式：0.1 与 0.2

Loom 0.1.4 同时读取 yohaku/0.1 和 yohaku/0.2。旧格式行为保留；reverse 生成的新 tex 使用 0.2，旧版 Loom 不识别 0.2，因此不会把需要精确末尾的新文件误生成成旧格式。

## 0.2：无笔记导入与精确末尾

最小文档：

````markdown
---
format: yohaku/0.2
target: text
macro: '[[macros/raw]]'
body_separator: true
---

## 正文
```text
print("lain kawaii")
```

## 输出与关联
```yaml
output: demo.py
```
````

上例 body_separator: true 表示结束围栏前的最后一个 LF 只是文档分隔符，不属于输出。因此输出是 `print("lain kawaii")`，末尾没有换行。若正文原本以 LF、CR 或 CRLF 结束，reverse 会原样保留它，不设置这个标志。空正文直接生成零字节文件。

body_separator 可省略或为布尔值；true 时必须存在一个可剔除的最终 LF。解析后的 body_byte_end 与 body 字段都已排除这个分隔符，生成、正文哈希、源映射使用相同的实际内容。不会依靠“通常 Python 需要换行”等猜测改写数据。

0.2 必须包含正文与输出区域；AI 笔记可以不存在。不存在时，不补 writer、summary、source_version 或任何语义记忆。若后续添加笔记区域，则仍验证正整数 source_version、非空 writer 与 summary。links 在两个格式里都可省略。

reverse 的 imported 头部记录实际导入路径、字节数和 SHA-256，是导入时的事实，不是用途推断或关联关系。编辑正文后，该字段仍指向导入时的内容；当前产物摘要由生成映射另外记录。

没有笔记时，映射 source_version_declared 为 null；有笔记时保留声明的正整数。note_authorship_verified 与 note_freshness_verified 仍为 false。新版 map 同时读取旧数字版本字段和新 null。

## 0.1：原有文档约定


源文件采用 UTF-8，无 BOM。本版默认演示文档使用暂定的 .txt；其他示例也保留 .source.md 写法。解析器不依赖源文档扩展名。

## 四部分

````markdown
---
format: yohaku/0.1
target: python
macro: '[[macros/raw]]'
tags: [示例, 输出文字]
---

## 正文
```python
print("lain baka")
```

## 输出与关联
```yaml
output: lain_baka.py
links: []
```

## AI 笔记
```yaml
source_version: 1
writer: mirai
summary: 输出一句文字。
```
````

顶部必须是以 --- 开始和结束的 YAML 映射。format 必须是 yohaku/0.1，target 是非空文字。build 的输入需要 macro；tags 可选，必须是文字列表，没有固定数量上限。

正文、输出与关联、AI 笔记三个区域各出现一次；它们可以交换顺序。区域外只接受这些标题与空行。每个区域有且仅有一个围栏代码块，元数据区域的块类型必须是 yaml 或 yml；正文块的类型自由。

正文从开始围栏下一行开始，到结束围栏前结束。内容字节、缩进、空行及原有 CR/LF/CRLF 保持一致；正文中的 Unicode 分隔字符不被当作物理换行。非空的最后一行正文必须有换行，结束围栏才能位于独立一行；这份围栏格式不直接表达“最后一行没有换行”的非空产物。空正文生成零字节文件。

围栏是至少三个相同的反引号或波浪号，允许 0～3 个前导空格。结束围栏须使用相同字符，长度不少于起始围栏，后面只能有空格或制表符。正文含有围栏时，用更长的外层围栏包住它。区域标题只在代码块外识别。

YAML 映射键要求文字，重复键在任意嵌套层级均报错。普通额外属性可以保留；元数据解析时将换行统一提供给 YAML 读取器，原始源文本和正文不变。必需属性请直接写在对应映射中，本版本不实现 YAML 合并键的继承约定。

## 输出、链接和笔记

output 相对于生成基准目录，不能为空、不能是绝对地址或已有目录。自 0.1.1 起默认以源文档实际所在的目录为基准；--root 可以指定其他基准。解析器处理常规路径别名与已有符号链接，防止输出覆盖当前输入或当前宏。0.1.2 起禁止输出到保留的 .loom 元数据目录，且不同源文档不能认领相同产物。基准目录不是访问权限沙箱。

默认示例 output 只写 lain_baka.py；直接传入 examples/lain_baka.txt 即可在源文档旁边生成文件。Loom 保留源文档，单独生成运行产物。

links 可省略或使用空列表。有内容时，每条关联是带 file、relation、description 三个非空文字字段的映射，例如：

```yaml
links:
  - file: '[[shared/colors]]'
    relation: uses
    description: 本程序使用其中定义的颜色。
```

这些资料留在源文本中，不自动插入导入语句或递归构建其他源文件。

AI 笔记必须提供正整数 source_version、非空 writer 和 summary；其他字段自由。Loom 只检查数据结构，不生成、修改、认证或判断笔记的新鲜程度。来源映射中的 note_authorship_verified 和 note_freshness_verified 均为 false。

## 宏

macro 使用 [[relative/path]] 引用，基准为文档所在目录或指定的 --root。不带扩展名时追加 .source.md；已经带有 .source.md 时不重复追加。

宏文件沿用外层格式，target 为 macro。通过引导读取器直接读取它的正文，不递归运行它的 macro 属性。其余输出和笔记区域照常保留，但执行转换时使用调用方的输出地址。

支持的唯一命令为：

```text
<%* emit(body, output) %>
```

命令的 token 之间允许空白和换行；标识符不能拆开。body 是调用方正文，output 是调用方的地址。宏只在被引用宏文件的正文中解释。普通正文的宏标记按字面输出；这套语法没有 eval、不执行 JavaScript、不执行生成的代码，也不承诺 Templater 兼容。

## 版本映射

映射路径为产物父目录/.loom/maps/产物名.构建摘要.json。构建摘要由源路径、源版本、宏版本、产物摘要和输出地址共同确定。相同输入重复构建使用同一映射；内容不同的既有同名映射不会被覆盖。

映射存储完整输入快照、正文的字节范围、生成行号与源行号、来源地址及声明的笔记版本。map 命令校验快照、范围、行号和实际产物字节，并以保存的源版本显示位置。摘要校验用于内容一致性，不认证作者身份。

0.1.2 的 build 登记产物来源，sync/watch 会删除同一来源的旧输出地址与旧映射，保留当前映射；源文件缺失时清理其记录中的产物和映射。仅清理仍具有正确归属且字节摘要吻合的普通文件。源格式、正文提取和宏语法没有改变。

