"""Review plan construction."""

from __future__ import annotations

from collections import defaultdict
from typing import Dict, Iterable, List

from .classifier import classify_comment, highest_severity, severity_score, text_similarity, top_category
from .models import CommentCluster, ReviewComment, ReviewPlan, SlicerConfig, WorkSlice


def build_review_plan(comments: Iterable[ReviewComment], config: SlicerConfig) -> ReviewPlan:
    classified = [classify_comment(comment, config) for comment in comments]
    open_comments = [comment for comment in classified if comment.state == "open"]
    clusters = cluster_comments(open_comments, config)
    slices = build_slices(clusters, config)
    duplicate_count = sum(cluster.duplicate_count for cluster in clusters)
    untriaged_count = sum(1 for comment in open_comments if not comment.path or comment.category == "untriaged")
    warnings = build_warnings(open_comments, clusters, duplicate_count, untriaged_count, config)
    gate_passed = not warnings
    return ReviewPlan(
        input_count=len(classified),
        open_count=len(open_comments),
        duplicate_count=duplicate_count,
        untriaged_count=untriaged_count,
        clusters=clusters,
        slices=slices,
        warnings=warnings,
        gate_passed=gate_passed,
        exit_code=0 if gate_passed else 1,
    )


def cluster_comments(comments: List[ReviewComment], config: SlicerConfig) -> List[CommentCluster]:
    clusters: List[List[ReviewComment]] = []
    for comment in sorted(comments, key=comment_sort_key):
        match_index = find_matching_cluster(comment, clusters, config)
        if match_index is None:
            clusters.append([comment])
        else:
            clusters[match_index].append(comment)
    result = [make_cluster(index, members, config) for index, members in enumerate(clusters, start=1)]
    return sorted(result, key=lambda item: (-item.score, item.category, item.title))


def find_matching_cluster(comment: ReviewComment, clusters: List[List[ReviewComment]], config: SlicerConfig) -> int:
    for index, members in enumerate(clusters):
        if not members:
            continue
        representative = members[0]
        if comment.category != representative.category:
            continue
        if text_similarity(comment, representative) >= config.duplicate_similarity:
            return index
        if comment.path and representative.path == comment.path and comment.line and representative.line and abs(comment.line - representative.line) <= 2:
            return index
    return None


def make_cluster(index: int, comments: List[ReviewComment], config: SlicerConfig) -> CommentCluster:
    severity = highest_severity(comment.severity for comment in comments)
    category = top_category(comment.category for comment in comments)
    files = sorted({comment.path for comment in comments if comment.path})
    score = min(100, severity_score(severity) + min(15, (len(comments) - 1) * 5) + min(10, max(0, len(files) - 1) * 3))
    title = summarize_comment(comments[0])
    duplicate_count = max(0, len(comments) - 1)
    reason = build_cluster_reason(comments, severity, category, files)
    return CommentCluster(
        id=f"C{index:03d}",
        title=title,
        comments=comments,
        severity=severity,
        category=category,
        files=files,
        duplicate_count=duplicate_count,
        score=score,
        owner=config.default_owner,
        reason=reason,
    )


def build_slices(clusters: List[CommentCluster], config: SlicerConfig) -> List[WorkSlice]:
    buckets: Dict[str, List[CommentCluster]] = defaultdict(list)
    for cluster in clusters:
        key = cluster.files[0] if cluster.files else f"untriaged:{cluster.category}"
        buckets[key].append(cluster)
    slices: List[WorkSlice] = []
    counter = 1
    for _, bucket in sorted(buckets.items(), key=lambda item: item[0]):
        current: List[CommentCluster] = []
        current_files: List[str] = []
        for cluster in sorted(bucket, key=lambda item: -item.score):
            proposed_files = sorted(set(current_files) | set(cluster.files))
            proposed_comments = sum(len(item.comments) for item in current) + len(cluster.comments)
            if current and (len(proposed_files) > config.max_slice_files or proposed_comments > config.max_slice_comments):
                slices.append(make_slice(counter, current, config))
                counter += 1
                current = []
                current_files = []
            current.append(cluster)
            current_files = sorted(set(current_files) | set(cluster.files))
        if current:
            slices.append(make_slice(counter, current, config))
            counter += 1
    return sorted(slices, key=lambda item: (-item.score, item.id))


def make_slice(index: int, clusters: List[CommentCluster], config: SlicerConfig) -> WorkSlice:
    severity = highest_severity(cluster.severity for cluster in clusters)
    category = top_category(cluster.category for cluster in clusters)
    files = sorted({path for cluster in clusters for path in cluster.files})
    score = min(100, max(cluster.score for cluster in clusters) + min(10, len(clusters) - 1))
    title = build_slice_title(category, files, clusters)
    checklist = build_checklist(clusters)
    return WorkSlice(
        id=f"S{index:03d}",
        title=title,
        clusters=clusters,
        files=files,
        severity=severity,
        category=category,
        owner=config.default_owner,
        score=score,
        checklist=checklist,
    )


def build_warnings(
    open_comments: List[ReviewComment],
    clusters: List[CommentCluster],
    duplicate_count: int,
    untriaged_count: int,
    config: SlicerConfig,
) -> List[str]:
    warnings: List[str] = []
    blockers = [cluster for cluster in clusters if cluster.severity == "blocker"]
    if config.fail_on_blocker and len(blockers) > config.max_open_blockers:
        warnings.append(f"open blocker clusters exceed limit: {len(blockers)} > {config.max_open_blockers}")
    if open_comments and duplicate_count / len(open_comments) > config.max_duplicate_ratio:
        warnings.append("duplicate review comment ratio is too high")
    if open_comments and untriaged_count / len(open_comments) > config.max_untriaged_ratio:
        warnings.append("too many open comments are missing path or category")
    if any(not cluster.files for cluster in clusters):
        warnings.append("some clusters cannot be assigned to files")
    return warnings


def summarize_comment(comment: ReviewComment) -> str:
    words = " ".join(comment.body.split())
    if len(words) <= 72:
        return words
    return words[:69].rstrip() + "..."


def build_cluster_reason(comments: List[ReviewComment], severity: str, category: str, files: List[str]) -> str:
    parts = [f"{len(comments)} open comment(s)", f"severity={severity}", f"category={category}"]
    if files:
        parts.append(f"files={len(files)}")
    else:
        parts.append("missing file path")
    return ", ".join(parts)


def build_slice_title(category: str, files: List[str], clusters: List[CommentCluster]) -> str:
    if files:
        if len(files) == 1:
            return f"{category}: fix review comments in {files[0]}"
        return f"{category}: fix review comments across {len(files)} files"
    return f"{category}: triage unassigned review comments"


def build_checklist(clusters: List[CommentCluster]) -> List[str]:
    items = []
    for cluster in clusters:
        first = cluster.comments[0]
        location = first.path or "unassigned file"
        if first.line:
            location = f"{location}:{first.line}"
        items.append(f"[{cluster.id}] {cluster.severity}/{cluster.category} at {location}: {cluster.title}")
    return items


def comment_sort_key(comment: ReviewComment):
    return (comment.path or "~", comment.line or 0, comment.category, comment.body)
