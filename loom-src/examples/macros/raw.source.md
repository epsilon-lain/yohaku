---
format: yohaku/0.1
target: macro
tags:
  - 转换
  - 原样输出
---

## 正文
```text
<%* emit(body, output) %>
```

## 输出与关联
```yaml
output: generated/raw.macro
links: []
```

## AI 笔记
```yaml
source_version: 1
writer: mirai
summary: 将调用方正文原样写到调用方的输出地址。
uncertainty: 第一版只支持一个 emit 命令，不是通用脚本解释器。
```

