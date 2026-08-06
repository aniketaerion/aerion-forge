"""Deterministic lexical search scoring."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryRecord
from forge.autonomous_memory.normalization import normalize_statement


@dataclass(frozen=True, slots=True)
class SearchScore:
    """Lexical relevance score and matched terms."""

    score: float
    matched_terms: tuple[str, ...]


def score_record(
    record: MemoryRecord,
    query_text: str,
) -> SearchScore:
    """Score normalized term overlap."""
    query_terms = {
        term
        for term in normalize_statement(query_text).split()
        if term
    }
    record_terms = set(
        record.normalized_statement.split()
    )

    if not query_terms:
        return SearchScore(
            score=0.0,
            matched_terms=(),
        )

    matched = tuple(sorted(query_terms & record_terms))
    score = len(matched) / len(query_terms)

    return SearchScore(
        score=round(score, 6),
        matched_terms=matched,
    )