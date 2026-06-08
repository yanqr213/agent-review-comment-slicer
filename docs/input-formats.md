# Input Formats / 输入格式

## 中文

`agent-review-comment-slicer` 支持 JSONL、JSON、CSV 三种输入。它面向 GitHub PR review comments、inline comments、review threads，也适合导入 AI reviewer 的输出。

推荐 JSONL：

```json
{"id":"r1","path":"src/app.py","line":42,"author":"reviewer","body":"Blocking: missing auth check.","severity":"blocker","category":"security"}
```

字段别名：

- 正文：`body`、`comment`、`text`、`message`
- 路径：`path`、`file`、`filename`
- 行号：`line`、`position`、`original_line`
- 作者：`author`、`user`、`reviewer`
- 状态：`state`、`status`
- 严重度：`severity`、`priority`
- 分类：`category`、`kind`、`topic`
- 修复建议：`suggestion`、`fix`、`resolution`

JSON 可以是数组，也可以是 `{ "comments": [...] }`。如果使用 `{ "reviewThreads": [...] }`，工具会把 thread 内的 comments 展平。

## English

The tool accepts JSONL, JSON, and CSV. It is designed for GitHub PR review comments, inline comments, review threads, and AI reviewer output.

JSON can be an array, a `{ "comments": [...] }` object, or a `{ "reviewThreads": [...] }` object. CSV uses the same field names and aliases.
