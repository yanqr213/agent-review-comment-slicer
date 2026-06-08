# Changelog / 变更记录

## 中文

### 0.2.0 - 2026-06-08

- 新增 `prompts` 输出格式，为每个 work slice 生成可直接交给 Codex、Claude Code、Cursor 等 agent 的修复提示词。
- `all` 输出现在包含 `agent-prompts/index.md` 和每个 slice 的独立 prompt 文件。
- 增加 prompt 渲染、CLI 格式解析和报告生成测试。
- 增加包 Repository / Changelog 元数据。
- 更新中英文 README、CI 文档和 agent playbook。

### 0.1.0 - 2026-06-08

- 首次公开版本。
- 支持 JSONL、JSON、CSV review comment 输入。
- 支持 GitHub-style `comments` 和 `reviewThreads` JSON 结构。
- 支持严重度和分类关键词配置。
- 支持重复评论聚类、agent work slice 生成、Markdown/JSON/JUnit 报告。
- 支持 blocker、重复率、未归类率 CI gate。

## English

### 0.2.0 - 2026-06-08

- Added a `prompts` output format that writes one ready-to-run fix prompt per work slice for Codex, Claude Code, Cursor, and similar agents.
- Included `agent-prompts/index.md` and per-slice prompt files in `all` output.
- Added tests for prompt rendering, CLI format parsing, and report generation.
- Added package Repository and Changelog metadata.
- Updated Chinese and English README, CI docs, and the agent playbook.

### 0.1.0 - 2026-06-08

- Initial public release.
- Supports JSONL, JSON, and CSV review comment input.
- Supports GitHub-style `comments` and `reviewThreads` JSON structures.
- Supports configurable severity and category keywords.
- Generates duplicate clusters, agent work slices, Markdown/JSON/JUnit reports, and CI gates.
