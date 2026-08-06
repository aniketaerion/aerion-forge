"""Repository-scoped memory access."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.errors import MemoryScopeError
from forge.autonomous_memory.models import (
    MemoryProvenance,
    MemoryRecord,
)
from forge.autonomous_memory.storage import MemoryStorage


@dataclass(frozen=True, slots=True)
class MemoryRepository:
    """Repository-scoped facade over storage."""

    storage: MemoryStorage
    repository_scope: str

    def save(
        self,
        record: MemoryRecord,
        provenance: MemoryProvenance,
    ) -> None:
        if record.repository_scope != self.repository_scope:
            raise MemoryScopeError(
                "Memory record repository scope mismatch."
            )

        self.storage.put_record(record)
        self.storage.put_provenance(provenance)

    def get(self, memory_id: str) -> MemoryRecord | None:
        record = self.storage.get_record(memory_id)

        if (
            record is not None
            and record.repository_scope
            != self.repository_scope
        ):
            return None

        return record

    def all(self) -> tuple[MemoryRecord, ...]:
        return tuple(
            record
            for record in self.storage.all_records()
            if record.repository_scope
            == self.repository_scope
        )