# Report Schema / 报告结构

## 中文

JSON 报告包含：

- `summary`：输入评论数、open 评论数、重复率、未归类率、cluster 数、slice 数和 gate 状态。
- `clusters`：去重后的评论簇，每个簇包含严重度、分类、文件、重复数、风险分和原始评论。
- `slices`：可交给 agent 的修复包，每个包包含文件列表、checklist 和关联 clusters。
- `warnings`：CI gate 失败原因。

JUnit 报告把每条 gate warning 转成 failure，方便在 GitHub Actions 页面直接看到失败原因。

SARIF 报告把每个去重后的 cluster 转成一个 Code Scanning result，并附带文件、行号、severity、category、重复数、score 和稳定 fingerprint。gate warning 会以 `review.gate` result 输出。

`prompts` 输出会写入：

- `agent-prompts/index.md`：所有 prompt 文件的索引、严重度、分类、分数和文件数。
- `agent-prompts/Sxxx.md`：单个 work slice 的 agent 修复提示词，包含范围、文件、checklist、原始评论摘要和完成规则。

## English

The JSON report contains `summary`, `clusters`, `slices`, and `warnings`. Each cluster keeps the original comments so a reviewer can audit the deduplication result. Each slice is designed to be assigned to one AI coding agent.

The SARIF report emits one GitHub Code Scanning result per deduplicated cluster, with file location, severity/category metadata, duplicate count, score, and a stable fingerprint. Gate warnings are emitted as `review.gate` results.

The `prompts` output writes `agent-prompts/index.md` plus one `agent-prompts/Sxxx.md` file per work slice. Each prompt scopes the assigned files, checklist, original review comments, and completion rules for one agent session.
