# Contributing / 贡献指南

## 中文

欢迎改进 agent-review-comment-slicer。项目原则：

- 保持离线、可解释、可审计。
- 不直接修改代码、不关闭评论、不调用外部服务。
- 新规则需要测试覆盖。
- README 和关键文档保持中文优先，并提供完整英文说明。

本地验证：

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m agent_review_comment_slicer --input examples/review-comments.jsonl --config examples/slicer.config.json --out reports --formats markdown,json,junit --no-fail
```

适合贡献的方向：

- 更多 review 平台导出字段别名。
- 更好的中文/英文关键词规则。
- 更细的 slice 策略。
- 更丰富的 CI gate。

## English

Contributions are welcome. Keep the project offline, explainable, and auditable. Do not add behavior that edits code, closes comments, or calls external services by default. New rules should include tests and documentation.
