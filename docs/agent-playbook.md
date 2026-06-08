# Agent Playbook / 智能体修复手册

## 中文

推荐流程：

1. 导出 PR review comments 或 AI reviewer 输出到 JSONL。
2. 运行 `agent-review-comment-slicer --no-fail` 生成计划。
3. 让 agent 一次只领取一个 `Sxxx` work slice。
4. agent 修复时必须引用 checklist 中的 `Cxxx` cluster id。
5. 修完后重新导入剩余 open comments，再跑严格模式。

给 agent 的任务模板：

```text
请处理 review slice S001。只处理 checklist 里的评论簇，不要顺手重构无关文件。
完成后列出：修复的 cluster id、改动文件、运行的验证命令、仍需人工确认的问题。
```

设计原则：评论切片要小、路径明确、风险可排序、重复评论要合并。这样多个 agent 并行修 review 时，不容易互相踩。

## English

Recommended workflow:

1. Export PR review comments or AI reviewer output to JSONL.
2. Run `agent-review-comment-slicer --no-fail`.
3. Assign one `Sxxx` work slice to each agent.
4. Require agents to reference `Cxxx` cluster ids in their delivery notes.
5. Re-run strict mode after resolved comments are removed or marked resolved.
