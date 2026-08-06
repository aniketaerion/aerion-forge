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
        existing = self._learning.get(learning.learning_id)

        if existing is not None and existing != learning:
            raise MemoryContractError(
                f"Conflicting learning record: "
                f"{learning.learning_id}"
            )

        self._learning[learning.learning_id] = learning

    def all_learning(self) -> tuple[LearningRecord, ...]:
        return tuple(
            self._learning[key]
            for key in sorted(self._learning)
        )