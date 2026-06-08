"""Input parsers for review comments."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import ReviewComment


def load_comments(path: str) -> List[ReviewComment]:
    source = Path(path)
    if not source.exists():
        raise ValueError(f"input file does not exist: {path}")
    suffix = source.suffix.lower()
    if suffix == ".jsonl":
        return parse_jsonl(source.read_text(encoding="utf-8"))
    if suffix == ".json":
        return parse_json(source.read_text(encoding="utf-8"))
    if suffix == ".csv":
        return parse_csv(source.read_text(encoding="utf-8"))
    raise ValueError("input must be .jsonl, .json, or .csv")


def parse_jsonl(text: str) -> List[ReviewComment]:
    comments: List[ReviewComment] = []
    for index, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        data = json.loads(line)
        if not isinstance(data, dict):
            raise ValueError(f"jsonl line {index} must be an object")
        comments.append(comment_from_mapping(data, index))
    return comments


def parse_json(text: str) -> List[ReviewComment]:
    data = json.loads(text)
    if isinstance(data, dict):
        if "comments" in data:
            data = data["comments"]
        elif "reviewThreads" in data:
            data = flatten_review_threads(data["reviewThreads"])
        else:
            data = [data]
    if not isinstance(data, list):
        raise ValueError("json input must be an object or array")
    comments: List[ReviewComment] = []
    for index, item in enumerate(data, start=1):
        if not isinstance(item, dict):
            raise ValueError(f"json item {index} must be an object")
        comments.append(comment_from_mapping(item, index))
    return comments


def parse_csv(text: str) -> List[ReviewComment]:
    comments: List[ReviewComment] = []
    reader = csv.DictReader(text.splitlines())
    for index, row in enumerate(reader, start=1):
        comments.append(comment_from_mapping(row, index))
    return comments


def flatten_review_threads(threads: Any) -> List[Dict[str, Any]]:
    if not isinstance(threads, list):
        raise ValueError("reviewThreads must be an array")
    rows: List[Dict[str, Any]] = []
    for thread_index, thread in enumerate(threads, start=1):
        if not isinstance(thread, dict):
            raise ValueError(f"reviewThreads item {thread_index} must be an object")
        thread_id = str(thread.get("id") or f"thread-{thread_index}")
        for comment_index, comment in enumerate(thread.get("comments") or [], start=1):
            if not isinstance(comment, dict):
                raise ValueError(f"thread {thread_id} comment {comment_index} must be an object")
            merged = dict(comment)
            merged.setdefault("thread_id", thread_id)
            merged.setdefault("path", thread.get("path", ""))
            rows.append(merged)
    return rows


def comment_from_mapping(data: Dict[str, Any], index: int) -> ReviewComment:
    body = first_present(data, ["body", "comment", "text", "message"])
    if body is None or not str(body).strip():
        raise ValueError(f"comment {index} is missing body/comment/text/message")
    return ReviewComment(
        id=str(first_present(data, ["id", "comment_id", "node_id"]) or f"comment-{index}"),
        body=str(body).strip(),
        path=str(first_present(data, ["path", "file", "filename"]) or ""),
        line=coerce_line(first_present(data, ["line", "position", "original_line"])),
        author=str(first_present(data, ["author", "user", "reviewer"]) or ""),
        thread_id=str(first_present(data, ["thread_id", "thread", "conversation_id"]) or ""),
        state=str(first_present(data, ["state", "status"]) or "open").lower(),
        severity=str(first_present(data, ["severity", "priority"]) or ""),
        category=str(first_present(data, ["category", "kind", "topic"]) or ""),
        suggestion=str(first_present(data, ["suggestion", "fix", "resolution"]) or ""),
        url=str(first_present(data, ["url", "html_url", "permalink"]) or ""),
    )


def first_present(data: Dict[str, Any], keys: Iterable[str]) -> Any:
    for key in keys:
        if key in data and data[key] not in (None, ""):
            return data[key]
    return None


def coerce_line(value: Any) -> int:
    if value in (None, ""):
        return None
    try:
        number = int(value)
    except (TypeError, ValueError):
        return None
    return number if number > 0 else None
