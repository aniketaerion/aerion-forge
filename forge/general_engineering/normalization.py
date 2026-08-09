"""Normalization helpers for M5.9 engineering requests."""

from __future__ import annotations

import re
from collections.abc import Iterable

_WHITESPACE = re.compile(r"\s+")
_BULLET_PREFIX = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s*")


def normalize_text(value: str) -> str:
    """Return stable single-line text while preserving semantic punctuation."""
    return _WHITESPACE.sub(" ", value.strip())


def normalize_optional_items(values: Iterable[str]) -> tuple[str, ...]:
    """Normalize, de-duplicate, and preserve input order."""
    result: list[str] = []
    seen: set[str] = set()

    for raw in values:
        cleaned = normalize_text(_BULLET_PREFIX.sub("", raw))
        if not cleaned:
            continue
        key = cleaned.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)

    return tuple(result)


def normalize_repository_path(value: str) -> str:
    """Normalize a repository-relative path without permitting traversal."""
    cleaned = normalize_text(value).replace("\\", "/")
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned