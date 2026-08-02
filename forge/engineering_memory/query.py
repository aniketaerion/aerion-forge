"""Read-only deterministic Engineering Memory queries."""

from forge.engineering_memory.errors import (
    EngineeringMemoryNotFoundError,
)
from forge.engineering_memory.models import (
    EngineeringMemoryGeneration,
    EngineeringMemoryStore,
    MemoryRecord,
    MemoryType,
)
from forge.engineering_memory.policies import normalize_tag


class EngineeringMemoryQuery:
    """Read-only deterministic queries over Engineering Memory."""

    def __init__(
        self,
        store: EngineeringMemoryStore,
    ) -> None:
        self._store = store.model_copy(deep=True)

    def get(
        self,
        memory_id: str,
    ) -> MemoryRecord:
        """Return one active memory record by ID."""

        normalized = memory_id.strip()

        if not normalized:
            raise EngineeringMemoryNotFoundError("Memory ID cannot be blank.")

        try:
            record = self._store.records[normalized]
        except KeyError as exc:
            raise EngineeringMemoryNotFoundError(
                f"Engineering Memory record not found: {normalized}"
            ) from exc

        return record.model_copy(deep=True)

    def list_all(
        self,
    ) -> tuple[MemoryRecord, ...]:
        """Return all active records in deterministic order."""

        return tuple(self.get(memory_id) for memory_id in sorted(self._store.records))

    def by_mission(
        self,
        mission_id: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records linked to one mission."""

        normalized = mission_id.strip()

        return tuple(record for record in self.list_all() if normalized in record.mission_ids)

    def by_task(
        self,
        task_id: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records linked to one task."""

        normalized = task_id.strip()

        return tuple(record for record in self.list_all() if normalized in record.task_ids)

    def by_assessment(
        self,
        assessment_id: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records linked to one assessment."""

        normalized = assessment_id.strip()

        return tuple(record for record in self.list_all() if normalized in record.assessment_ids)

    def by_capability(
        self,
        capability_id: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records linked to one capability."""

        normalized = capability_id.strip()

        return tuple(record for record in self.list_all() if normalized in record.capability_ids)

    def by_milestone(
        self,
        milestone: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records linked to one milestone."""

        normalized = milestone.strip()

        return tuple(record for record in self.list_all() if normalized in record.milestones)

    def by_type(
        self,
        memory_type: MemoryType,
    ) -> tuple[MemoryRecord, ...]:
        """Return records with one controlled memory type."""

        return tuple(record for record in self.list_all() if record.memory_type is memory_type)

    def by_tag(
        self,
        tag: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records containing one normalized tag."""

        normalized = normalize_tag(tag)

        return tuple(record for record in self.list_all() if normalized in record.tags)

    def related_to(
        self,
        memory_id: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return records directly related to one memory record."""

        normalized = memory_id.strip()

        if not normalized:
            raise EngineeringMemoryNotFoundError("Memory ID cannot be blank.")

        self.get(normalized)

        related_ids: set[str] = set()

        for record in self.list_all():
            for relationship in record.relationships:
                if relationship.source_memory_id == normalized:
                    related_ids.add(relationship.target_memory_id)

                if relationship.target_memory_id == normalized:
                    related_ids.add(relationship.source_memory_id)

        return tuple(
            self.get(related_id)
            for related_id in sorted(related_ids)
            if related_id in self._store.records
        )

    def history(
        self,
        memory_id: str,
    ) -> tuple[MemoryRecord, ...]:
        """Return historical versions for one memory ID."""

        normalized = memory_id.strip()

        return tuple(
            record.model_copy(deep=True)
            for record in self._store.history.get(
                normalized,
                [],
            )
        )

    def generation(
        self,
    ) -> EngineeringMemoryGeneration | None:
        """Return active generation metadata."""

        if self._store.generation is None:
            return None

        return self._store.generation.model_copy(deep=True)

    def statistics(
        self,
    ) -> dict[str, int]:
        """Return deterministic aggregate query statistics."""

        records = self.list_all()

        return {
            "records": len(records),
            "relationships": sum(len(record.relationships) for record in records),
            "evidence": sum(len(record.evidence) for record in records),
            "missions": len(
                {mission_id for record in records for mission_id in record.mission_ids}
            ),
            "tasks": len({task_id for record in records for task_id in record.task_ids}),
            "assessments": len(
                {assessment_id for record in records for assessment_id in record.assessment_ids}
            ),
            "capabilities": len(
                {capability_id for record in records for capability_id in record.capability_ids}
            ),
            "permanent": sum(record.retention_policy.value == "permanent" for record in records),
        }
