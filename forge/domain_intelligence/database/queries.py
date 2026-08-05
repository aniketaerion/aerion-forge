"""SQL query classification for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

_QUERY_PATTERNS = {
    "select": re.compile(r"\bSELECT\b", re.IGNORECASE),
    "insert": re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
    "update": re.compile(r"\bUPDATE\b", re.IGNORECASE),
    "delete": re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
}


def classify_queries(
    sql: str,
) -> dict[str, int]:
    """Count basic SQL query types."""
    return {
        name: len(pattern.findall(sql))
        for name, pattern in sorted(_QUERY_PATTERNS.items())
    }


def classify_query_file(
    path: Path,
) -> dict[str, int]:
    """Classify queries in one file."""
    return classify_queries(
        path.read_text(encoding="utf-8-sig")
    )