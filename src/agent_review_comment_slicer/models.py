"""Data models for review slicing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class SlicerConfig:
    severity_keywords: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "blocker": ["security", "secret", "data loss", "breaks", "must fix", "blocking", "漏洞", "阻塞", "必须"],
            "high": ["race", "crash", "incorrect", "regression", "unsafe", "权限", "崩溃", "错误"],
            "medium": ["edge case", "missing test", "validation", "retry", "边界", "测试", "校验"],
            "low": ["nit", "style", "typo", "rename", "格式", "命名", "拼写"],
        }
    )
    category_keywords: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "security": ["security", "secret", "token", "credential", "auth", "权限", "密钥", "鉴权"],
            "correctness": ["bug", "incorrect", "logic", "edge case", "off by", "错误", "边界", "逻辑"],
            "tests": ["test", "coverage", "fixture", "assert", "测试", "覆盖"],
            "docs": ["readme", "docs", "comment", "documentation", "文档", "注释"],
            "maintainability": ["refactor", "duplicate", "complex", "naming", "重复", "复杂", "命名"],
        }
    )
    duplicate_similarity: float = 0.82
    max_slice_comments: int = 5
    max_slice_files: int = 3
    fail_on_blocker: bool = True
    max_open_blockers: int = 0
    max_duplicate_ratio: float = 0.35
    max_untriaged_ratio: float = 0.25
    default_owner: str = "agent"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "severity_keywords": self.severity_keywords,
            "category_keywords": self.category_keywords,
            "duplicate_similarity": self.duplicate_similarity,
            "max_slice_comments": self.max_slice_comments,
            "max_slice_files": self.max_slice_files,
            "fail_on_blocker": self.fail_on_blocker,
            "max_open_blockers": self.max_open_blockers,
            "max_duplicate_ratio": self.max_duplicate_ratio,
            "max_untriaged_ratio": self.max_untriaged_ratio,
            "default_owner": self.default_owner,
        }


@dataclass
class ReviewComment:
    id: str
    body: str
    path: str = ""
    line: Optional[int] = None
    author: str = ""
    thread_id: str = ""
    state: str = "open"
    severity: str = ""
    category: str = ""
    suggestion: str = ""
    url: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "body": self.body,
            "path": self.path,
            "line": self.line,
            "author": self.author,
            "thread_id": self.thread_id,
            "state": self.state,
            "severity": self.severity,
            "category": self.category,
            "suggestion": self.suggestion,
            "url": self.url,
        }


@dataclass
class CommentCluster:
    id: str
    title: str
    comments: List[ReviewComment]
    severity: str
    category: str
    files: List[str]
    duplicate_count: int
    score: int
    owner: str
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "category": self.category,
            "files": self.files,
            "duplicate_count": self.duplicate_count,
            "score": self.score,
            "owner": self.owner,
            "reason": self.reason,
            "comments": [comment.to_dict() for comment in self.comments],
        }


@dataclass
class WorkSlice:
    id: str
    title: str
    clusters: List[CommentCluster]
    files: List[str]
    severity: str
    category: str
    owner: str
    score: int
    checklist: List[str]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "severity": self.severity,
            "category": self.category,
            "owner": self.owner,
            "score": self.score,
            "files": self.files,
            "checklist": self.checklist,
            "clusters": [cluster.to_dict() for cluster in self.clusters],
        }


@dataclass
class ReviewPlan:
    input_count: int
    open_count: int
    duplicate_count: int
    untriaged_count: int
    clusters: List[CommentCluster]
    slices: List[WorkSlice]
    warnings: List[str]
    gate_passed: bool
    exit_code: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": {
                "input_count": self.input_count,
                "open_count": self.open_count,
                "duplicate_count": self.duplicate_count,
                "duplicate_ratio": round(self.duplicate_count / self.input_count, 4) if self.input_count else 0.0,
                "untriaged_count": self.untriaged_count,
                "untriaged_ratio": round(self.untriaged_count / self.input_count, 4) if self.input_count else 0.0,
                "cluster_count": len(self.clusters),
                "slice_count": len(self.slices),
                "gate_passed": self.gate_passed,
                "exit_code": self.exit_code,
            },
            "clusters": [cluster.to_dict() for cluster in self.clusters],
            "slices": [work_slice.to_dict() for work_slice in self.slices],
            "warnings": list(self.warnings),
        }
