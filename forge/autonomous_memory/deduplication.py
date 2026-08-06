"""Exact deterministic memory deduplication."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryRecord


@dataclass(frozen=True, slots=True)
class DeduplicationResult:
    records: tuple[MemoryRecord, ...]
    duplicate_memory_ids: tuple[str, ...]


def semantic_key(record: MemoryRecord) -> tuple[str, str, str]:
    return (
        record.repository_scope,
        record.memory_kind.value,
        record.normalized_statement,
    )


def deduplicate_records(
    records: tuple[MemoryRecord, ...],
) -> DeduplicationResult:
    seen: set[tuple[str, str, str]] = set()
    accepted: list[MemoryRecord] = []
    duplicates: list[str] = []

    for record in sorted(records, key=lambda item: item.memory_id):
        key = semantic_key(record)
        if key in seen:
            duplicates.append(record.memory_id)
            continue
        seen.add(key)
        accepted.append(record)

    return DeduplicationResult(
        records=tuple(accepted),
        duplicate_memory_ids=tuple(duplicates),
    )