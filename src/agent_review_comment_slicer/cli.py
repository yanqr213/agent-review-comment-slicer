"""Command-line interface."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List

from . import __version__
from .config import explain_config, load_config
from .parser import load_comments
from .planner import build_review_plan
from .reports import write_reports


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-review-comment-slicer",
        description="Slice PR/code review comments into reviewable AI-agent work packages.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--input", required=False, help="review comments in JSONL, JSON, or CSV")
    parser.add_argument("--config", help="JSON config path")
    parser.add_argument("--out", default="reports", help="report output directory")
    parser.add_argument("--formats", default="markdown,json,junit", help="comma-separated report formats: markdown,json,junit,all")
    parser.add_argument("--no-fail", action="store_true", help="always exit 0 after writing reports")
    parser.add_argument("--print-config", action="store_true", help="print effective config and exit")
    return parser


def main(argv: List[str] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        if args.print_config:
            print(explain_config(config))
            return 0
        if not args.input:
            raise ValueError("--input is required unless --print-config is used")
        comments = load_comments(args.input)
        plan = build_review_plan(comments, config)
        write_reports(plan, Path(args.out), parse_formats(args.formats))
        print(
            f"Agent Review Comment Slicer: {plan.open_count} open comments, "
            f"{len(plan.clusters)} clusters, {len(plan.slices)} slices. Gate: "
            f"{'pass' if plan.gate_passed else 'fail'}. Reports: {args.out}"
        )
        return 0 if args.no_fail else plan.exit_code
    except (OSError, ValueError) as exc:
        print(f"agent-review-comment-slicer: {exc}")
        return 2


def parse_formats(value: str) -> List[str]:
    result = [item.strip().lower() for item in value.split(",") if item.strip()]
    allowed = {"markdown", "md", "json", "junit", "all"}
    unknown = [item for item in result if item not in allowed]
    if unknown:
        raise ValueError(f"unknown report format(s): {', '.join(unknown)}")
    return result or ["markdown", "json", "junit"]
