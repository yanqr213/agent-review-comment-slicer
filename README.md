# agent-review-comment-slicer

agent-review-comment-slicer 是一个离线的 PR/code review 评论归并与任务切片工具，专门服务于使用 Codex、Claude Code、Cursor 或自研 AI coding agent 的团队。它把 GitHub review comments、inline comments、review threads、AI reviewer 输出整理成：

- 去重后的问题簇。
- 按文件、严重度、分类排序的 agent 修复包。
- 面向 reviewer 的 Markdown 报告。
- 面向自动化的 JSON 报告。
- 面向 CI 的 JUnit gate。
- 面向 GitHub Code Scanning 的 SARIF 报告。
- 面向 Codex、Claude Code、Cursor 等 agent 的逐 slice 修复 prompt。

它不调用 GitHub API，不调用模型，也不修改代码。你只需要把评论导出成 JSONL、JSON 或 CSV，本工具就能在本地或 CI 中稳定运行。

## 为什么有用

AI reviewer 和多人 code review 很容易产生这些问题：

- 同一个根因被多次评论，agent 会重复修。
- 阻塞评论、低优先级 nit、测试建议混在一起。
- 评论散落在多个文件，无法直接分派给多个 agent。
- 有些评论缺路径、缺分类、缺严重度，CI 无法判断是否可合并。
- reviewer 想知道“剩下的评论能不能切成小包交给 agent 并行处理”。

本工具聚焦这件事：**review comments/threads -> 去重问题簇 -> agent work slices -> CI gate**。

## 安装

```bash
python -m pip install -e .
```

不安装也可以运行：

```bash
PYTHONPATH=src python -m agent_review_comment_slicer --input examples/review-comments.jsonl --no-fail
```

## 快速开始

```bash
agent-review-comment-slicer \
  --input examples/review-comments.jsonl \
  --config examples/slicer.config.json \
  --out reports \
  --formats markdown,json,junit,sarif,prompts \
  --no-fail
```

输出文件：

- `review-plan.md`：给 reviewer 和 agent 看的工作包清单。
- `review-plan.json`：给自动化、仪表盘或二次脚本使用。
- `junit.xml`：给 CI 展示 gate warning。
- `review-plan.sarif`：给 GitHub Code Scanning 展示去重后的 blocker/security/correctness 等 review cluster。
- `agent-prompts/index.md`：每个 work slice 对应的 agent prompt 索引。
- `agent-prompts/S001.md` 等：可直接粘给一个 agent session 的修复提示词。

## 输入格式

推荐 JSONL：

```json
{"id":"r1","path":"src/auth/session.py","line":42,"body":"Blocking: token is stored in plain text.","severity":"blocker","category":"security"}
```

也支持 JSON 数组、`{"comments":[...]}`、`{"reviewThreads":[...]}` 和 CSV。字段别名见 [docs/input-formats.md](docs/input-formats.md)。

## CLI

```bash
agent-review-comment-slicer [options]
```

常用参数：

- `--input`：JSONL、JSON 或 CSV 评论文件。
- `--config`：JSON 配置文件。
- `--out`：报告输出目录。
- `--formats`：`markdown,json,junit,sarif,prompts,all`。
- `--no-fail`：只生成报告，不用 gate 状态影响退出码。
- `--print-config`：打印有效默认配置。

## 配置

```json
{
  "duplicate_similarity": 0.82,
  "max_slice_comments": 5,
  "max_slice_files": 3,
  "fail_on_blocker": true,
  "max_open_blockers": 0,
  "max_duplicate_ratio": 0.35,
  "max_untriaged_ratio": 0.25,
  "default_owner": "agent"
}
```

你可以配置严重度关键词和分类关键词。默认支持英文和常见中文词，例如“阻塞”“必须”“测试”“权限”“密钥”。

## 工作模型

1. 读取评论。
2. 标准化状态、路径、严重度和分类。
3. 用文本相似度、文件路径和行号把重复评论合并成 cluster。
4. 按文件、评论数、文件数限制切成 slice。
5. 生成 checklist，方便一个 agent 只处理一个 slice。
6. 生成每个 slice 的 agent 修复 prompt。
7. 根据 blocker、重复率、未归类率生成 CI gate。

## CI 集成

```yaml
- name: Slice review comments
  run: |
    agent-review-comment-slicer \
      --input review-comments.jsonl \
      --out reports/review-comments \
      --formats markdown,json,junit,sarif,prompts
```

更多示例见 [docs/ci.md](docs/ci.md)。

## 开发

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
PYTHONPATH=src python -m agent_review_comment_slicer \
  --input examples/review-comments.jsonl \
  --config examples/slicer.config.json \
  --out reports \
  --formats markdown,json,junit,prompts \
  --no-fail
```

## 限制

- 不直接调用 GitHub API；评论导出由你自己的脚本或 CI 步骤完成。
- 不调用 LLM；分类使用可解释关键词和本地启发式。
- 相似度去重是保守启发式，重要评论仍应由 reviewer 审阅。
- 不修改代码、不关闭评论、不提交 PR。

## English

agent-review-comment-slicer is an offline review comment triage and task slicing tool for teams that use Codex, Claude Code, Cursor, or internal AI coding agents.

It turns GitHub review comments, inline comments, review threads, and AI reviewer output into deduplicated issue clusters, small agent work slices, Markdown/JSON reports, SARIF for GitHub Code Scanning, per-slice agent fix prompts, and CI-ready JUnit gates.

### Use Cases

- Deduplicate repeated AI reviewer comments.
- Separate blockers from low-priority nits.
- Group comments by file and category.
- Assign one small review slice to each coding agent.
- Generate one ready-to-run fix prompt per review slice.
- Upload deduplicated review clusters to GitHub Code Scanning via SARIF.
- Fail CI when open blockers remain, duplicate noise is too high, or too many comments are missing path/category metadata.

### Install

```bash
python -m pip install -e .
```

### CLI

```bash
agent-review-comment-slicer \
  --input examples/review-comments.jsonl \
  --config examples/slicer.config.json \
  --out reports \
  --formats markdown,json,junit,sarif,prompts
```

Important options:

- `--input`: JSONL, JSON, or CSV review comments.
- `--config`: JSON configuration.
- `--out`: report output directory.
- `--formats`: `markdown,json,junit,sarif,prompts,all`.
- `--no-fail`: report-only mode.
- `--print-config`: print effective defaults.

### Model

The tool classifies comments, merges likely duplicates into clusters, then builds work slices that are small enough for one agent to handle. Each slice includes files, severity, category, score, an actionable checklist, and an optional prompt file under `agent-prompts/`.

### Limits

The tool does not call GitHub, call an LLM, edit code, close comments, or submit pull requests. It is a local planner and CI gate.
