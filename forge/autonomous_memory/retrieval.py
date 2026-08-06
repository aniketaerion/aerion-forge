"""Scope-filtered deterministic memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from forge.autonomous_memory.models import (
    MemoryMatch,
    MemoryQuery,
    MemoryRecord,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.search import score_record
from forge.autonomous_memory.states import MemoryStatus
from forge.autonomous_memory.storage import MemoryStorage


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """Retrieved records and scoring metadata."""

    records: tuple[MemoryRecord, ...]
    matches: tuple[MemoryMatch, ...]


def _recency_score(record: MemoryRecord) -> float:
    now = datetime.now(UTC)
    age_days = max(
        0.0,
        (now - record.created_at).total_seconds()
        / 86400.0,
    )
    return round(max(0.0, 1.0 - age_days / 365.0), 6)


def _applicability_score(
    record: MemoryRecord,
    query: MemoryQuery,
) -> float:
    score = 0.50

    if record.repository_scope == query.repository_scope:
        score += 0.30

    if (
        query.module_scope
        and set(query.module_scope)
        & set(record.module_scope)
    ):
        score += 0.10

    if (
        query.capability_scope
        and set(query.capability_scope)
        & set(record.capability_scope)
    ):
        score += 0.10

    return round(min(score, 1.0), 6)


def retrieve_memory(
    *,
    storage: MemoryStorage,
    query: MemoryQuery,
    query_text: str,
    policy: AutonomousMemoryPolicy,
) -> RetrievalResult:
    """Retrieve bounded repository-scoped memory."""
    limit = min(
        query.maximum_results,
        policy.limits.maximum_query_results,
    )

    scored: list[tuple[MemoryRecord, MemoryMatch]] = []

    for record in storage.all_records():
        if record.repository_scope != query.repository_scope:
            continue

        if (
            not query.include_superseded
            and record.status is not MemoryStatus.ACTIVE
        ):
            continue

        if record.confidence < query.minimum_confidence:
            continue

        if (
            query.memory_kinds
            and record.memory_kind not in query.memory_kinds
        ):
            continue

        if query.tags and not set(query.tags).issubset(
            set(record.tags)
        ):
            continue

        search = score_record(record, query_text)
        applicability = _applicability_score(
            record,
            query,
        )
        recency = _recency_score(record)
        total = round(
            0.40 * search.score
            + 0.30 * applicability
            + 0.20 * record.confidence
            + 0.10 * recency,
            6,
        )

        match = MemoryMatch(
            memory_id=record.memory_id,
            relevance_score=search.score,
            confidence_score=record.confidence,
            recency_score=recency,
            applicability_score=applicability,
            total_score=total,
            matched_terms=search.matched_terms,
            rationale=(
                "Ranked by lexical relevance, applicability, "
                "confidence, and recency."
            ),
        )
        scored.append((record, match))

    scored.sort(
        key=lambda item: (
            -item[1].total_score,
            -item[1].applicability_score,
            -item[1].confidence_score,
            -item[1].recency_score,
            item[0].memory_id,
        )
    )

    selected = scored[:limit]

    return RetrievalResult(
        records=tuple(item[0] for item in selected),
        matches=tuple(item[1] for item in selected),
    )