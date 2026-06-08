# Report Schema / 报告结构

## 中文

JSON 报告包含：

- `summary`：输入评论数、open 评论数、重复率、未归类率、cluster 数、slice 数和 gate 状态。
- `clusters`：去重后的评论簇，每个簇包含严重度、分类、文件、重复数、风险分和原始评论。
- `slices`：可交给 agent 的修复包，每个包包含文件列表、checklist 和关联 clusters。
- `warnings`：CI gate 失败原因。

JUnit 报告把每条 gate warning 转成 failure，方便在 GitHub Actions 页面直接看到失败原因。

## English

The JSON report contains `summary`, `clusters`, `slices`, and `warnings`. Each cluster keeps the original comments so a reviewer can audit the deduplication result. Each slice is designed to be assigned to one AI coding agent.
