"""Deterministic memory normalization."""

from __future__ import annotations

import re
import unicodedata

_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^a-z0-9\s._:/-]+")


def normalize_statement(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = _NON_WORD.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def normalize_tags(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = {
        normalize_statement(value).replace(" ", "-")
        for value in values
        if normalize_statement(value)
    }
    return tuple(sorted(normalized))


def normalize_scope(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value.strip().replace("\\", "/")
                for value in values
                if value.strip()
            }
        )
    )