---
format: yohaku/0.1
target: python
macro: '[[macros/raw]]'
tags: [示例, 报错定位]
---

## 正文
```python
value = 0
print(1 / value)
```

## 输出与关联
```yaml
output: generated/runtime_error.py
links: []
```

## AI 笔记
```yaml
source_version: 1
writer: mirai
summary: 故意除以零，用于演示外部 Python 报错对应的源文本位置。
connections: 使用 macros/raw；Python 运行器负责产生运行报错。
location: 正文第二行发生除零。
uncertainty: 本文件故意不能正常运行；Loom 只负责原样生成。
```
