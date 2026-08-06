[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.5-autonomous-memory-learning"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.5 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_memory\storage.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_memory\repository.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_memory\indexing.py" @'
"""Deterministic in-memory memory index."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_memory.models import MemoryRecord


@dataclass(slots=True)
class MemoryIndex:
    """Index memory by repository, tags, modules, and capabilities."""

    _repository: dict[str, set[str]] = field(
        default_factory=dict
    )
    _tags: dict[str, set[str]] = field(default_factory=dict)
    _modules: dict[str, set[str]] = field(
        default_factory=dict
    )
    _capabilities: dict[str, set[str]] = field(
        default_factory=dict
    )

    def add(self, record: MemoryRecord) -> None:
        self._repository.setdefault(
            record.repository_scope,
            set(),
        ).add(record.memory_id)

        for tag in record.tags:
            self._tags.setdefault(tag, set()).add(
                record.memory_id
            )

        for module in record.module_scope:
            self._modules.setdefault(module, set()).add(
                record.memory_id
            )

        for capability in record.capability_scope:
            self._capabilities.setdefault(
                capability,
                set(),
            ).add(record.memory_id)

    def candidates(
        self,
        *,
        repository_scope: str,
        tags: tuple[str, ...] = (),
        module_scope: tuple[str, ...] = (),
        capability_scope: tuple[str, ...] = (),
    ) -> tuple[str, ...]:
        candidate_ids = set(
            self._repository.get(repository_scope, set())
        )

        for tag in tags:
            candidate_ids &= self._tags.get(tag, set())

        for module in module_scope:
            candidate_ids &= self._modules.get(
                module,
                set(),
            )

        for capability in capability_scope:
            candidate_ids &= self._capabilities.get(
                capability,
                set(),
            )

        return tuple(sorted(candidate_ids))
'@

Write-Utf8NoBom "forge\autonomous_memory\search.py" @'
"""Deterministic lexical search scoring."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryRecord
from forge.autonomous_memory.normalization import normalize_statement


@dataclass(frozen=True, slots=True)
class SearchScore:
    """Lexical relevance score and matched terms."""

    score: float
    matched_terms: tuple[str, ...]


def score_record(
    record: MemoryRecord,
    query_text: str,
) -> SearchScore:
    """Score normalized term overlap."""
    query_terms = {
        term
        for term in normalize_statement(query_text).split()
        if term
    }
    record_terms = set(
        record.normalized_statement.split()
    )

    if not query_terms:
        return SearchScore(
            score=0.0,
            matched_terms=(),
        )

    matched = tuple(sorted(query_terms & record_terms))
    score = len(matched) / len(query_terms)

    return SearchScore(
        score=round(score, 6),
        matched_terms=matched,
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\retrieval.py" @'
"""Scope-filtered deterministic memory retrieval."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

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
    now = datetime.now(timezone.utc)
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
'@

Write-Utf8NoBom "forge\autonomous_memory\retention.py" @'
"""Retention and status filtering."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from forge.autonomous_memory.models import MemoryRecord
from forge.autonomous_memory.states import (
    MemoryStatus,
    RetentionClass,
)


@dataclass(frozen=True, slots=True)
class RetentionDecision:
    """Retention decision for one memory record."""

    retain: bool
    target_status: MemoryStatus
    rationale: str


def evaluate_retention(
    record: MemoryRecord,
    *,
    maximum_temporary_age_days: int = 30,
) -> RetentionDecision:
    """Evaluate deterministic retention policy."""
    if record.status in {
        MemoryStatus.QUARANTINED,
        MemoryStatus.DISPUTED,
    }:
        return RetentionDecision(
            retain=True,
            target_status=record.status,
            rationale="Exceptional status remains retained.",
        )

    if record.retention_class is not RetentionClass.TEMPORARY:
        return RetentionDecision(
            retain=True,
            target_status=record.status,
            rationale="Non-temporary memory remains retained.",
        )

    age_days = (
        datetime.now(timezone.utc) - record.created_at
    ).total_seconds() / 86400.0

    if age_days > maximum_temporary_age_days:
        return RetentionDecision(
            retain=True,
            target_status=MemoryStatus.EXPIRED,
            rationale="Temporary memory exceeded retention age.",
        )

    return RetentionDecision(
        retain=True,
        target_status=record.status,
        rationale="Temporary memory remains within retention age.",
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\memory_service.py" @'
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
'@

Write-Utf8NoBom "tests\test_autonomous_memory_storage.py" @'
import pytest

from forge.autonomous_memory.errors import MemoryContractError
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def record(statement: str) -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement=statement,
        normalized_statement=statement.casefold(),
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )


def test_identical_write_is_idempotent() -> None:
    storage = InMemoryMemoryStorage()
    item = record("Possible constraint.")

    storage.put_record(item)
    storage.put_record(item)

    assert storage.get_record("memory-1") == item


def test_conflicting_write_is_rejected() -> None:
    storage = InMemoryMemoryStorage()
    storage.put_record(record("First statement."))

    with pytest.raises(MemoryContractError):
        storage.put_record(record("Different statement."))
'@

Write-Utf8NoBom "tests\test_autonomous_memory_repository.py" @'
import pytest

from forge.autonomous_memory.errors import MemoryScopeError
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryProvenance,
    MemoryRecord,
)
from forge.autonomous_memory.repository import MemoryRepository
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    RetentionClass,
)
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_repository_rejects_cross_scope_memory() -> None:
    storage = InMemoryMemoryStorage()
    repository = MemoryRepository(
        storage=storage,
        repository_scope="repository-a",
    )
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=0.5,
        repository_scope="repository-b",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository-b",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )
    provenance = MemoryProvenance(
        provenance_id="provenance-1",
        memory_id="memory-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="source-1",
        evidence_digest="digest-1",
        repository_fingerprint="fingerprint-1",
        actor="Aerion",
    )

    with pytest.raises(MemoryScopeError):
        repository.save(record, provenance)
'@

Write-Utf8NoBom "tests\test_autonomous_memory_indexing.py" @'
from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def test_index_filters_by_repository_and_tag() -> None:
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        tags=("architecture",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )
    index = MemoryIndex()
    index.add(record)

    assert index.candidates(
        repository_scope="repository",
        tags=("architecture",),
    ) == ("memory-1",)
'@

Write-Utf8NoBom "tests\test_autonomous_memory_search.py" @'
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.search import score_record
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def test_search_scores_term_overlap() -> None:
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Repository uses Python.",
        normalized_statement="repository uses python",
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )

    result = score_record(
        record,
        "python repository",
    )

    assert result.score == 1.0
    assert result.matched_terms == (
        "python",
        "repository",
    )
'@

Write-Utf8NoBom "tests\test_autonomous_memory_retrieval.py" @'
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryQuery,
    MemoryRecord,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.retrieval import retrieve_memory
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_retrieval_is_repository_scoped() -> None:
    storage = InMemoryMemoryStorage()

    for memory_id, repository in (
        ("memory-1", "repository-a"),
        ("memory-2", "repository-b"),
    ):
        storage.put_record(
            MemoryRecord(
                memory_id=memory_id,
                memory_kind=MemoryKind.REPOSITORY_FACT,
                statement="Repository uses Python.",
                normalized_statement="repository uses python",
                confidence=0.9,
                repository_scope=repository,
                evidence_references=("evidence-1",),
                source_references=("source-1",),
                applicability=MemoryApplicability(
                    kind=ApplicabilityKind.EXACT_REPOSITORY,
                    repository_scope=repository,
                    rationale="Repository scoped.",
                ),
                retention_class=RetentionClass.PROJECT_LIFETIME,
            )
        )

    result = retrieve_memory(
        storage=storage,
        query=MemoryQuery(
            query_id="query-1",
            repository_scope="repository-a",
            requested_by="Aerion",
        ),
        query_text="python repository",
        policy=AutonomousMemoryPolicy(),
    )

    assert tuple(
        record.memory_id
        for record in result.records
    ) == ("memory-1",)
'@

Write-Utf8NoBom "tests\test_autonomous_memory_retention.py" @'
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.retention import (
    evaluate_retention,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemoryStatus,
    RetentionClass,
)


def test_permanent_memory_is_retained() -> None:
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.ARCHITECTURE_CONSTRAINT,
        statement="Execution requires approval.",
        normalized_statement="execution requires approval",
        confidence=0.9,
        repository_scope="repository",
        evidence_references=("evidence-1",),
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.PERMANENT,
    )

    result = evaluate_retention(record)

    assert result.retain
    assert result.target_status is MemoryStatus.ACTIVE
'@

Write-Utf8NoBom "tests\test_autonomous_memory_service.py" @'
from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.memory_service import (
    AutonomousMemoryService,
)
from forge.autonomous_memory.models import (
    MemoryObservation,
    MemoryQuery,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.states import MemorySourceKind
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)


def test_service_ingests_and_retrieves_memory() -> None:
    service = AutonomousMemoryService(
        policy=AutonomousMemoryPolicy(),
        storage=InMemoryMemoryStorage(),
        index=MemoryIndex(),
    )

    result = service.ingest(
        MemoryObservation(
            observation_id="observation-1",
            source_kind=MemorySourceKind.REPOSITORY,
            source_reference="forge/module.py",
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            content="Repository uses Python.",
            evidence_references=("evidence-1",),
        ),
        actor="Aerion",
    )

    retrieved = service.retrieve(
        query=MemoryQuery(
            query_id="query-1",
            repository_scope="repository",
            requested_by="Aerion",
        ),
        query_text="python repository",
    )

    assert retrieved.records[0].memory_id == (
        result.record.memory_id
    )
'@

Write-Host ""
Write-Host "M5.5 Package 2 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_memory_storage.py `
    .\tests\test_autonomous_memory_repository.py `
    .\tests\test_autonomous_memory_indexing.py `
    .\tests\test_autonomous_memory_search.py `
    .\tests\test_autonomous_memory_retrieval.py `
    .\tests\test_autonomous_memory_retention.py `
    .\tests\test_autonomous_memory_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.5 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.5 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short