"""Storage contracts and in-memory implementation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from forge.autonomous_memory.errors import MemoryContractError
from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryProvenance,
    MemoryRecord,
)


class MemoryStorage(Protocol):
    """Persistence boundary for autonomous memory."""

    def put_record(self, record: MemoryRecord) -> None: ...

    def get_record(self, memory_id: str) -> MemoryRecord | None: ...

    def all_records(self) -> tuple[MemoryRecord, ...]: ...

    def put_provenance(
        self,
        provenance: MemoryProvenance,
    ) -> None: ...

    def provenance_for_memory(
        self,
        memory_id: str,
    ) -> tuple[MemoryProvenance, ...]: ...

    def put_learning(
        self,
        learning: LearningRecord,
    ) -> None: ...

    def all_learning(self) -> tuple[LearningRecord, ...]: ...


@dataclass(slots=True)
class InMemoryMemoryStorage:
    """Deterministic append-only memory storage."""

    _records: dict[str, MemoryRecord] = field(
        default_factory=dict
    )
    _provenance: dict[str, list[MemoryProvenance]] = field(
        default_factory=dict
    )
    _learning: dict[str, LearningRecord] = field(
        default_factory=dict
    )

    def put_record(self, record: MemoryRecord) -> None:
        existing = self._records.get(record.memory_id)

        if existing is not None and existing != record:
            raise MemoryContractError(
                f"Conflicting memory record: {record.memory_id}"
            )

        self._records[record.memory_id] = record

    def get_record(
        self,
        memory_id: str,
    ) -> MemoryRecord | None:
        return self._records.get(memory_id)

    def all_records(self) -> tuple[MemoryRecord, ...]:
        return tuple(
            self._records[key]
            for key in sorted(self._records)
        )

    def put_provenance(
        self,
        provenance: MemoryProvenance,
    ) -> None:
        values = self._provenance.setdefault(
            provenance.memory_id,
            [],
        )

        if provenance not in values:
            values.append(provenance)
            values.sort(
                key=lambda item: item.provenance_id
            )

    def provenance_for_memory(
        self,
        memory_id: str,
    ) -> tuple[MemoryProvenance, ...]:
        return tuple(
            self._provenance.get(memory_id, ())
        )

    def put_learning(
        self,
        learning: LearningRecord,
    ) -> None:
        """Store a new or monotonically updated learning record."""
        existing = self._learning.get(learning.learning_id)

        if existing is None:
            self._learning[learning.learning_id] = learning
            return

        if existing == learning:
            return

        identity_unchanged = (
            existing.source_memory_ids
            == learning.source_memory_ids
            and existing.lesson == learning.lesson
            and existing.applicability
            == learning.applicability
            and existing.created_at == learning.created_at
        )
        counters_are_monotonic = (
            learning.success_count
            >= existing.success_count
            and learning.failure_count
            >= existing.failure_count
        )

        if not identity_unchanged:
            raise MemoryContractError(
                "Learning update changed immutable identity fields: "
                f"{learning.learning_id}"
            )

        if not counters_are_monotonic:
            raise MemoryContractError(
                "Learning feedback counters cannot decrease: "
                f"{learning.learning_id}"
            )

        self._learning[learning.learning_id] = learning
    def all_learning(self) -> tuple[LearningRecord, ...]:
        return tuple(
            self._learning[key]
            for key in sorted(self._learning)
        )