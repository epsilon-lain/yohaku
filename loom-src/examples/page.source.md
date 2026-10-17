---
format: yohaku/0.1
target: html
macro: '[[macros/raw]]'
tags: [示例, html]
---

## 正文
````html
<!doctype html>
<html lang="zh-CN">
<meta charset="utf-8">
<title>Loom</title>
<h1>Yohaku · Loom</h1>
<p>人与 AI 共同编辑源文本，Loom 按规则生成文件。</p>
</html>
````

## 输出与关联
```yaml
output: generated/page.html
links: []
```

## AI 笔记
```yaml
source_version: 1
writer: mirai
summary: 一份可在浏览器打开的静态 HTML 页面。
connections: 使用 macros/raw 原样生成，无其他源码依赖。
uncertainty: 转换不校验目标语言的语法或笔记作者身份。
```
