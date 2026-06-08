"""Comment classification and similarity helpers."""

from __future__ import annotations

import re
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Set

from .models import ReviewComment, SlicerConfig


SEVERITY_ORDER = {"blocker": 4, "high": 3, "medium": 2, "low": 1, "info": 0}


def classify_comment(comment: ReviewComment, config: SlicerConfig) -> ReviewComment:
    severity = normalize_label(comment.severity)
    category = normalize_label(comment.category)
    text = f"{comment.body} {comment.suggestion}".lower()
    if not severity:
        severity = match_keywords(text, config.severity_keywords) or "info"
    if not category:
        category = match_keywords(text, config.category_keywords) or infer_category_from_path(comment.path)
    return ReviewComment(
        id=comment.id,
        body=comment.body,
        path=normalize_path(comment.path),
        line=comment.line,
        author=comment.author,
        thread_id=comment.thread_id,
        state=normalize_state(comment.state),
        severity=severity,
        category=category,
        suggestion=comment.suggestion,
        url=comment.url,
    )


def normalize_label(value: str) -> str:
    return str(value or "").strip().lower().replace(" ", "-")


def normalize_state(value: str) -> str:
    state = normalize_label(value)
    if state in {"resolved", "closed", "done", "dismissed"}:
        return "resolved"
    return "open"


def normalize_path(path: str) -> str:
    return str(path or "").replace("\\", "/").strip()


def match_keywords(text: str, rules: Dict[str, List[str]]) -> str:
    for label, keywords in rules.items():
        for keyword in keywords:
            if keyword.lower() in text:
                return label
    return ""


def infer_category_from_path(path: str) -> str:
    lower = normalize_path(path).lower()
    if not lower:
        return "untriaged"
    if "test" in lower or "spec" in lower:
        return "tests"
    if lower.endswith((".md", ".rst", ".txt")) or "/docs/" in f"/{lower}":
        return "docs"
    if "auth" in lower or "security" in lower:
        return "security"
    return "correctness"


def fingerprint(comment: ReviewComment) -> str:
    words = tokenize(comment.body)
    important = [word for word in words if word not in STOP_WORDS]
    stem = " ".join(important[:40])
    location = f"{comment.path}:{comment.line or ''}"
    return f"{comment.category}|{location}|{stem}"


def text_similarity(left: ReviewComment, right: ReviewComment) -> float:
    if left.path and right.path and left.path != right.path:
        path_bonus = 0.0
    else:
        path_bonus = 0.1
    body_score = SequenceMatcher(None, normalize_text(left.body), normalize_text(right.body)).ratio()
    category_bonus = 0.1 if left.category == right.category else 0.0
    line_bonus = 0.05 if left.line and right.line and abs(left.line - right.line) <= 3 else 0.0
    return min(1.0, body_score + path_bonus + category_bonus + line_bonus)


def tokenize(value: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_\u4e00-\u9fff]+", value.lower())


def normalize_text(value: str) -> str:
    return " ".join(tokenize(value))


def highest_severity(values: Iterable[str]) -> str:
    return max(values, key=lambda item: SEVERITY_ORDER.get(item, 0), default="info")


def severity_score(severity: str) -> int:
    return {"blocker": 95, "high": 75, "medium": 50, "low": 25, "info": 10}.get(severity, 10)


def top_category(values: Iterable[str]) -> str:
    counts: Dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))[0][0] if counts else "untriaged"


STOP_WORDS: Set[str] = {
    "a",
    "an",
    "and",
    "are",
    "be",
    "for",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "please",
    "should",
    "the",
    "this",
    "to",
    "we",
}
