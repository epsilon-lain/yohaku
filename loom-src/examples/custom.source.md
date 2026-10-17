---
format: yohaku/0.1
target: custom-format
macro: '[[macros/raw]]'
tags: [示例, custom-format]
---

## 正文
````custom-format
world = "Yohaku"
unit = "meter"
converter = "Loom"
````

## 输出与关联
```yaml
output: generated/world.custom
links: []
```

## AI 笔记
```yaml
source_version: 1
writer: mirai
summary: 自定义键值文本，证明输出扩展名不受固定列表限制。
connections: 使用 macros/raw 原样生成，无其他源码依赖。
uncertainty: 转换不校验目标语言的语法或笔记作者身份。
```
