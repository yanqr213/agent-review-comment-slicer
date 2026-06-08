"""Report rendering."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Iterable

from .models import ReviewPlan


def write_reports(plan: ReviewPlan, out_dir: Path, formats: Iterable[str]) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    requested = set(formats)
    if "all" in requested:
        requested = {"markdown", "json", "junit"}
    outputs = {}
    if "markdown" in requested or "md" in requested:
        path = out_dir / "review-plan.md"
        write_text(path, render_markdown(plan))
        outputs["markdown"] = str(path)
    if "json" in requested:
        path = out_dir / "review-plan.json"
        write_json(path, plan.to_dict())
        outputs["json"] = str(path)
    if "junit" in requested:
        path = out_dir / "junit.xml"
        write_text(path, render_junit(plan))
        outputs["junit"] = str(path)
    return outputs


def render_markdown(plan: ReviewPlan) -> str:
    summary = plan.to_dict()["summary"]
    lines = [
        "# Agent Review Comment Plan",
        "",
        f"- Input comments: {summary['input_count']}",
        f"- Open comments: {summary['open_count']}",
        f"- Clusters: {summary['cluster_count']}",
        f"- Work slices: {summary['slice_count']}",
        f"- Duplicate ratio: {summary['duplicate_ratio']}",
        f"- Untriaged ratio: {summary['untriaged_ratio']}",
        f"- Gate passed: {'yes' if plan.gate_passed else 'no'}",
        "",
        "## Work Slices",
        "",
        "| Slice | Severity | Score | Category | Files | Title |",
        "| --- | --- | ---: | --- | ---: | --- |",
    ]
    if not plan.slices:
        lines.append("| - | info | 0 | none | 0 | No open review comments. |")
    for work_slice in plan.slices:
        lines.append(
            f"| {work_slice.id} | {work_slice.severity} | {work_slice.score} | {work_slice.category} | "
            f"{len(work_slice.files)} | {escape_pipe(work_slice.title)} |"
        )
    lines.extend(["", "## Clusters", "", "| Cluster | Severity | Duplicates | Category | Files | Comment |", "| --- | --- | ---: | --- | --- | --- |"])
    if not plan.clusters:
        lines.append("| - | info | 0 | none | - | No clusters. |")
    for cluster in plan.clusters:
        files = ", ".join(cluster.files) if cluster.files else "-"
        lines.append(f"| {cluster.id} | {cluster.severity} | {cluster.duplicate_count} | {cluster.category} | `{escape_pipe(files)}` | {escape_pipe(cluster.title)} |")
    if plan.warnings:
        lines.extend(["", "## Gate Warnings", ""])
        for warning in plan.warnings:
            lines.append(f"- {warning}")
    lines.extend(["", "## Agent Checklists", ""])
    for work_slice in plan.slices:
        lines.append(f"### {work_slice.id} {work_slice.title}")
        lines.append("")
        for item in work_slice.checklist:
            lines.append(f"- [ ] {item}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def render_junit(plan: ReviewPlan) -> str:
    failures = plan.warnings
    tests = max(1, len(plan.slices) + len(plan.warnings))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<testsuite name="agent-review-comment-slicer" tests="{tests}" failures="{len(failures)}">',
    ]
    if not plan.slices and not plan.warnings:
        lines.append('  <testcase classname="agent_review_comment_slicer" name="no_open_comments" />')
    for work_slice in plan.slices:
        lines.append(f'  <testcase classname="agent_review_comment_slicer.slice" name="{html.escape(work_slice.id)}" />')
    for index, warning in enumerate(plan.warnings, start=1):
        lines.append(f'  <testcase classname="agent_review_comment_slicer.gate" name="warning_{index}">')
        lines.append(f'    <failure message="{html.escape(warning)}" type="gate">{html.escape(warning)}</failure>')
        lines.append("  </testcase>")
    lines.append("</testsuite>")
    return "\n".join(lines) + "\n"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)


def escape_pipe(value: str) -> str:
    return str(value).replace("|", "\\|")
