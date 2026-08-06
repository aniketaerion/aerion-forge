"""Application service for ingesting and retrieving memory."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.ingestion import (
    IngestionResult,
    MemoryIngestionService,
)
from forge.autonomous_memory.models import (
    MemoryObservation,
    MemoryQuery,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.repository import MemoryRepository
from forge.autonomous_memory.retrieval import (
    RetrievalResult,
    retrieve_memory,
)
from forge.autonomous_memory.states import MemoryKind
from forge.autonomous_memory.storage import MemoryStorage


@dataclass(slots=True)
class AutonomousMemoryService:
    """Coordinate ingestion, storage, indexing, and retrieval."""

    policy: AutonomousMemoryPolicy
    storage: MemoryStorage
    index: MemoryIndex

    def ingest(
        self,
        observation: MemoryObservation,
        *,
        actor: str,
        memory_kind: MemoryKind | None = None,
        module_scope: tuple[str, ...] = (),
        capability_scope: tuple[str, ...] = (),
        business_domain: str | None = None,
    ) -> IngestionResult:
        result = MemoryIngestionService(
            policy=self.policy
        ).ingest(
            observation,
            actor=actor,
            memory_kind=memory_kind,
            module_scope=module_scope,
            capability_scope=capability_scope,
            business_domain=business_domain,
        )

        repository = MemoryRepository(
            storage=self.storage,
            repository_scope=result.record.repository_scope,
        )
        repository.save(
            result.record,
            result.provenance,
        )
        self.index.add(result.record)

        return result

    def retrieve(
        self,
        *,
        query: MemoryQuery,
        query_text: str,
    ) -> RetrievalResult:
        return retrieve_memory(
            storage=self.storage,
            query=query,
            query_text=query_text,
            policy=self.policy,
        )