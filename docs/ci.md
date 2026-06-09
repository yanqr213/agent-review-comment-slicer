# CI Integration / CI 集成

## 中文

这个工具适合放在 review 收口阶段：当评论太多、重复太多、阻塞项没有切成可执行包时，让 CI 给出清晰失败。

```yaml
name: review-comment-slicing

on:
  pull_request:

jobs:
  slice-comments:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: python -m pip install agent-review-comment-slicer
      - name: Slice review comments
        run: |
          agent-review-comment-slicer \
            --input review-comments.jsonl \
            --config slicer.config.json \
            --out reports/review-comments \
            --formats markdown,json,junit,sarif,prompts
      - uses: actions/upload-artifact@v4
        if: always()
        with:
          name: review-comment-plan
          path: reports/review-comments
      - uses: github/codeql-action/upload-sarif@v3
        if: always()
        with:
          sarif_file: reports/review-comments/review-plan.sarif
```

团队常用 gate：

- `fail_on_blocker=true`：阻塞评论未处理时失败。
- `max_duplicate_ratio`：AI reviewer 重复评论过多时失败。
- `max_untriaged_ratio`：缺路径或缺分类的评论过多时失败。

`reports/review-comments/agent-prompts/` 会包含一个索引和每个 slice 的独立 prompt，可以作为 artifact 分发给多个 agent session。

`review-plan.sarif` 会把去重后的 cluster 作为 GitHub Code Scanning result。`blocker` / `high` 映射为 `error`，`medium` 映射为 `warning`，`low` 映射为 `note`；gate warning 会作为 `review.gate` result 出现。

## English

Use this tool near the end of review when comments need to be turned into actionable AI-agent work packages. It can fail CI when blockers remain open, duplicate review noise is too high, or too many comments are missing path/category metadata.

Include `prompts` in `--formats` when you want CI artifacts to contain ready-to-run prompt files under `agent-prompts/`.

Include `sarif` in `--formats` when you want deduplicated review clusters to appear in GitHub Code Scanning. Blocker/high clusters map to `error`, medium clusters map to `warning`, low clusters map to `note`, and gate warnings are emitted as `review.gate` results.
