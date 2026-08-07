"""M5.5 memory integration for mission planning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.identifiers import memory_query_identifier
from forge.autonomous_memory.memory_service import AutonomousMemoryService
from forge.autonomous_memory.models import MemoryQuery
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import MissionRequest


@dataclass(frozen=True, slots=True)
class MissionMemoryContext:
    query_id: str
    memory_ids: tuple[str, ...]
    evidence_references: tuple[str, ...]


@dataclass(slots=True)
class MissionMemoryIntegration:
    """Retrieve repository-scoped memory for one mission."""

    service: AutonomousMemoryService

    def retrieve(
        self,
        *,
        request: MissionRequest,
        context: MissionEngineeringContext,
    ) -> MissionMemoryContext:
        query_payload = {
            "repository_scope": context.workspace.repository_root,
            "capability_scope": context.capabilities.capability_ids,
            "requested_by": request.requested_by,
            "statement": request.statement,
        }
        query_id = memory_query_identifier(query_payload)
        query = MemoryQuery(
            query_id=query_id,
            repository_scope=context.workspace.repository_root,
            capability_scope=context.capabilities.capability_ids,
            requested_by=request.requested_by,
        )
        result = self.service.retrieve(
            query=query,
            query_text=request.statement,
        )

        memory_ids = tuple(
            match.memory_id
            for match in result.matches
        )

        evidence = tuple(
            f"memory:{memory_id}"
            for memory_id in memory_ids
        )

        return MissionMemoryContext(
            query_id=query_id,
            memory_ids=memory_ids,
            evidence_references=evidence,
        )