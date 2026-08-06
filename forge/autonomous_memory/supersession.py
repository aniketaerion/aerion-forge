"""Immutable supersession rules for autonomous memory."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.errors import MemorySupersessionError
from forge.autonomous_memory.models import MemoryRecord
from forge.autonomous_memory.states import MemoryStatus


@dataclass(frozen=True, slots=True)
class SupersessionResult:
    """Original record and its superseding replacement."""

    superseded: MemoryRecord
    replacement: MemoryRecord


def assert_no_supersession_cycle(
    *,
    replacement: MemoryRecord,
    existing_records: tuple[MemoryRecord, ...],
) -> None:
    """Reject direct or indirect supersession cycles."""
    by_id = {
        record.memory_id: record
        for record in existing_records
    }

    current = replacement.supersedes_memory_id
    visited: set[str] = {replacement.memory_id}

    while current is not None:
        if current in visited:
            raise MemorySupersessionError(
                "Supersession cycle detected."
            )

        visited.add(current)
        record = by_id.get(current)

        if record is None:
            return

        current = record.supersedes_memory_id


def apply_supersession(
    *,
    previous: MemoryRecord,
    replacement: MemoryRecord,
    existing_records: tuple[MemoryRecord, ...],
) -> SupersessionResult:
    """Return immutable superseded and replacement records."""
    if replacement.supersedes_memory_id != previous.memory_id:
        raise MemorySupersessionError(
            "Replacement must reference the memory it supersedes."
        )

    if previous.memory_id == replacement.memory_id:
        raise MemorySupersessionError(
            "Memory cannot supersede itself."
        )

    if previous.repository_scope != replacement.repository_scope:
        raise MemorySupersessionError(
            "Supersession cannot cross repository scope."
        )

    assert_no_supersession_cycle(
        replacement=replacement,
        existing_records=existing_records,
    )

    superseded = previous.model_copy(
        update={"status": MemoryStatus.SUPERSEDED}
    )

    return SupersessionResult(
        superseded=superseded,
        replacement=replacement,
    )