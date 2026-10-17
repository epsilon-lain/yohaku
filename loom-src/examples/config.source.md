---
format: yohaku/0.1
target: json
macro: '[[macros/raw]]'
tags: [示例, json]
---

## 正文
````json
{
  "name": "Yohaku",
  "converter": "Loom",
  "uses_ai_for_conversion": false
}
````

## 输出与关联
```yaml
output: generated/config.json
links: []
```

## AI 笔记
```yaml
source_version: 1
writer: mirai
summary: 记录名称和转换方式的 JSON 配置。
connections: 使用 macros/raw 原样生成，无其他源码依赖。
uncertainty: 转换不校验目标语言的语法或笔记作者身份。
```
