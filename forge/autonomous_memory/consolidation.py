"""Deterministic memory consolidation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryRecord


@dataclass(frozen=True, slots=True)
class ConsolidationGroup:
    """Group of semantically identical memory records."""

    canonical: MemoryRecord
    members: tuple[MemoryRecord, ...]


def consolidate_records(
    records: tuple[MemoryRecord, ...],
) -> tuple[ConsolidationGroup, ...]:
    """Group exact semantic duplicates without deleting history."""
    groups: dict[
        tuple[str, str, str],
        list[MemoryRecord],
    ] = {}

    for record in records:
        key = (
            record.repository_scope,
            record.memory_kind.value,
            record.normalized_statement,
        )
        groups.setdefault(key, []).append(record)

    consolidated: list[ConsolidationGroup] = []

    for key in sorted(groups):
        members = tuple(
            sorted(
                groups[key],
                key=lambda item: (
                    -item.confidence,
                    item.memory_id,
                ),
            )
        )
        consolidated.append(
            ConsolidationGroup(
                canonical=members[0],
                members=members,
            )
        )

    return tuple(consolidated)