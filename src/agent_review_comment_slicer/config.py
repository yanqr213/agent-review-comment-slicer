"""Configuration loading."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from .models import SlicerConfig


def load_config(path: str = None) -> SlicerConfig:
    config = SlicerConfig()
    if not path:
        validate_config(config)
        return config
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    allowed = set(config.to_dict())
    unknown = sorted(set(data) - allowed)
    if unknown:
        raise ValueError(f"unknown config keys: {', '.join(unknown)}")
    for key, value in data.items():
        setattr(config, key, value)
    validate_config(config)
    return config


def validate_config(config: SlicerConfig) -> None:
    for key in ["severity_keywords", "category_keywords"]:
        value = getattr(config, key)
        if not isinstance(value, dict):
            raise ValueError(f"{key} must be an object")
        for label, keywords in value.items():
            if not isinstance(label, str) or not isinstance(keywords, list) or not all(isinstance(item, str) for item in keywords):
                raise ValueError(f"{key} must map strings to lists of strings")
    if not isinstance(config.duplicate_similarity, (int, float)) or not 0 <= config.duplicate_similarity <= 1:
        raise ValueError("duplicate_similarity must be between 0 and 1")
    if not isinstance(config.max_slice_comments, int) or config.max_slice_comments < 1:
        raise ValueError("max_slice_comments must be a positive integer")
    if not isinstance(config.max_slice_files, int) or config.max_slice_files < 1:
        raise ValueError("max_slice_files must be a positive integer")
    if not isinstance(config.fail_on_blocker, bool):
        raise ValueError("fail_on_blocker must be boolean")
    if not isinstance(config.max_open_blockers, int) or config.max_open_blockers < 0:
        raise ValueError("max_open_blockers must be a non-negative integer")
    for key in ["max_duplicate_ratio", "max_untriaged_ratio"]:
        value = getattr(config, key)
        if not isinstance(value, (int, float)) or not 0 <= value <= 1:
            raise ValueError(f"{key} must be between 0 and 1")
    if not isinstance(config.default_owner, str) or not config.default_owner.strip():
        raise ValueError("default_owner must be a non-empty string")


def explain_config(config: SlicerConfig) -> str:
    return json.dumps(config.to_dict(), indent=2, ensure_ascii=False, sort_keys=True)
