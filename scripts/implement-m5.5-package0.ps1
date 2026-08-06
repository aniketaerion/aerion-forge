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

    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

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
    throw "M5.5 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_memory\errors.py" @'
"""Typed errors for autonomous memory and learning."""

class AutonomousMemoryError(RuntimeError):
    """Base error for autonomous-memory failures."""


class MemoryContractError(AutonomousMemoryError):
    """Raised when a memory contract is invalid."""


class MemoryIdentifierError(AutonomousMemoryError):
    """Raised when a stable identifier cannot be created."""


class MemoryPolicyError(AutonomousMemoryError):
    """Raised when memory policy is unsafe."""


class MemoryRedactionError(AutonomousMemoryError):
    """Raised when prohibited content is detected."""


class MemorySupersessionError(AutonomousMemoryError):
    """Raised when supersession is invalid."""


class MemoryScopeError(AutonomousMemoryError):
    """Raised when memory crosses an invalid scope."""
'@

Write-Utf8NoBom "forge\autonomous_memory\states.py" @'
"""Enumerations for autonomous memory and learning."""

from enum import StrEnum


class MemoryKind(StrEnum):
    REPOSITORY_FACT = "repository_fact"
    ARCHITECTURE_CONSTRAINT = "architecture_constraint"
    BUSINESS_RULE = "business_rule"
    IMPLEMENTATION_DECISION = "implementation_decision"
    VALIDATION_OUTCOME = "validation_outcome"
    EXECUTION_OUTCOME = "execution_outcome"
    FAILURE_PATTERN = "failure_pattern"
    RECOVERY_PATTERN = "recovery_pattern"
    ENGINEERING_LESSON = "engineering_lesson"
    USER_PREFERENCE = "user_preference"
    HYPOTHESIS = "hypothesis"
    NEGATIVE_EVIDENCE = "negative_evidence"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    QUARANTINED = "quarantined"


class MemorySourceKind(StrEnum):
    MISSION = "mission"
    SESSION = "session"
    DECISION = "decision"
    EXECUTION = "execution"
    VALIDATION = "validation"
    REPOSITORY = "repository"
    HUMAN_CORRECTION = "human_correction"
    ARCHITECTURE_REVIEW = "architecture_review"


class RetentionClass(StrEnum):
    PERMANENT = "permanent"
    LONG_LIVED = "long_lived"
    PROJECT_LIFETIME = "project_lifetime"
    BOUNDED = "bounded"
    TEMPORARY = "temporary"
    QUARANTINED = "quarantined"


class ApplicabilityKind(StrEnum):
    EXACT_REPOSITORY = "exact_repository"
    MODULE = "module"
    CAPABILITY = "capability"
    BUSINESS_DOMAIN = "business_domain"
    CROSS_PROJECT = "cross_project"
'@

Write-Utf8NoBom "forge\autonomous_memory\identifiers.py" @'
"""Stable deterministic identifiers for autonomous memory."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from forge.autonomous_memory.errors import MemoryIdentifierError


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }
    if isinstance(value, list | tuple | set | frozenset):
        items = [_normalize(item) for item in value]
        if isinstance(value, set | frozenset):
            items = sorted(
                items,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        return items
    return value


def deterministic_memory_identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    if not prefix.strip():
        raise MemoryIdentifierError(
            "Identifier prefix cannot be empty."
        )

    try:
        canonical = json.dumps(
            _normalize(payload),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
    except (TypeError, ValueError) as exc:
        raise MemoryIdentifierError(
            f"Unable to serialize payload for {prefix}."
        ) from exc

    digest = hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()[:24]

    return f"{prefix}-{digest}"


def memory_observation_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-observation",
        payload,
    )


def memory_record_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-record",
        payload,
    )


def memory_provenance_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-provenance",
        payload,
    )


def memory_query_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "memory-query",
        payload,
    )


def learning_record_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_memory_identifier(
        "learning-record",
        payload,
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\policies.py" @'
"""Default-safe policies for autonomous memory."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_memory.errors import MemoryPolicyError


class MemoryLimitPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_observation_characters: int = Field(
        default=20000,
        ge=100,
        le=500000,
    )
    maximum_tags: int = Field(default=20, ge=0, le=100)
    maximum_evidence_references: int = Field(
        default=50,
        ge=0,
        le=500,
    )
    maximum_query_results: int = Field(
        default=20,
        ge=1,
        le=200,
    )


class MemoryConfidencePolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    minimum_fact_confidence: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )
    minimum_lesson_confidence: float = Field(
        default=0.60,
        ge=0.0,
        le=1.0,
    )
    minimum_query_confidence: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
    )


class MemorySafetyPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    require_provenance: bool = True
    facts_require_evidence: bool = True
    reject_secrets: bool = True
    repository_scope_by_default: bool = True
    include_superseded_by_default: bool = False
    allow_cross_repository_retrieval: bool = False
    allow_repository_mutation: bool = False
    allow_tool_execution: bool = False
    allow_automatic_policy_update: bool = False
    current_repository_evidence_wins: bool = True

    @model_validator(mode="after")
    def validate_safety(self) -> MemorySafetyPolicy:
        violations: list[str] = []

        if not self.require_provenance:
            violations.append("provenance is mandatory")
        if not self.facts_require_evidence:
            violations.append("facts require evidence")
        if not self.reject_secrets:
            violations.append("secret rejection is mandatory")
        if not self.repository_scope_by_default:
            violations.append("repository scope is mandatory")
        if self.include_superseded_by_default:
            violations.append(
                "superseded memory must be hidden by default"
            )
        if self.allow_cross_repository_retrieval:
            violations.append(
                "cross-repository retrieval requires approval"
            )
        if self.allow_repository_mutation:
            violations.append(
                "M5.5 cannot mutate repositories"
            )
        if self.allow_tool_execution:
            violations.append("M5.5 cannot execute tools")
        if self.allow_automatic_policy_update:
            violations.append(
                "memory cannot update policy automatically"
            )
        if not self.current_repository_evidence_wins:
            violations.append(
                "current repository evidence must outrank memory"
            )

        if violations:
            raise MemoryPolicyError("; ".join(violations))

        return self


class AutonomousMemoryPolicy(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    policy_version: str = "1.0"
    limits: MemoryLimitPolicy = Field(
        default_factory=MemoryLimitPolicy
    )
    confidence: MemoryConfidencePolicy = Field(
        default_factory=MemoryConfidencePolicy
    )
    safety: MemorySafetyPolicy = Field(
        default_factory=MemorySafetyPolicy
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\models.py" @'
"""Immutable contracts for autonomous memory and learning."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    MemoryStatus,
    RetentionClass,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenMemoryContract(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class MemoryObservation(FrozenMemoryContract):
    observation_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    source_kind: MemorySourceKind
    source_reference: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    mission_id: str | None = None
    session_id: str | None = None
    content: str = Field(min_length=1, max_length=500000)
    evidence_references: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    observed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_collections(self) -> MemoryObservation:
        if len(set(self.evidence_references)) != len(
            self.evidence_references
        ):
            raise ValueError(
                "evidence_references cannot contain duplicates."
            )
        if len(set(self.tags)) != len(self.tags):
            raise ValueError("tags cannot contain duplicates.")
        return self


class MemoryApplicability(FrozenMemoryContract):
    kind: ApplicabilityKind
    repository_scope: str = Field(min_length=1)
    module_scope: tuple[str, ...] = ()
    capability_scope: tuple[str, ...] = ()
    business_domain: str | None = None
    rationale: str = Field(min_length=1)


class MemoryRecord(FrozenMemoryContract):
    memory_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    memory_kind: MemoryKind
    statement: str = Field(min_length=1)
    normalized_statement: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    repository_scope: str = Field(min_length=1)
    module_scope: tuple[str, ...] = ()
    capability_scope: tuple[str, ...] = ()
    business_domain: str | None = None
    evidence_references: tuple[str, ...] = ()
    source_references: tuple[str, ...] = Field(min_length=1)
    tags: tuple[str, ...] = ()
    applicability: MemoryApplicability
    retention_class: RetentionClass
    status: MemoryStatus = MemoryStatus.ACTIVE
    supersedes_memory_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_record(self) -> MemoryRecord:
        fact_like = {
            MemoryKind.REPOSITORY_FACT,
            MemoryKind.ARCHITECTURE_CONSTRAINT,
            MemoryKind.BUSINESS_RULE,
        }

        if (
            self.memory_kind in fact_like
            and not self.evidence_references
        ):
            raise ValueError(
                "Fact-like memory requires evidence."
            )

        if self.supersedes_memory_id == self.memory_id:
            raise ValueError(
                "Memory cannot supersede itself."
            )

        return self


class MemoryProvenance(FrozenMemoryContract):
    provenance_id: str = Field(min_length=1)
    memory_id: str = Field(min_length=1)
    source_kind: MemorySourceKind
    source_reference: str = Field(min_length=1)
    evidence_digest: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    actor: str = Field(min_length=1)
    captured_at: datetime = Field(default_factory=utc_now)


class MemoryQuery(FrozenMemoryContract):
    query_id: str = Field(min_length=1)
    repository_scope: str = Field(min_length=1)
    module_scope: tuple[str, ...] = ()
    capability_scope: tuple[str, ...] = ()
    business_domain: str | None = None
    memory_kinds: tuple[MemoryKind, ...] = ()
    tags: tuple[str, ...] = ()
    minimum_confidence: float = Field(
        default=0.40,
        ge=0.0,
        le=1.0,
    )
    maximum_results: int = Field(default=20, ge=1, le=200)
    include_superseded: bool = False
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class MemoryMatch(FrozenMemoryContract):
    memory_id: str = Field(min_length=1)
    relevance_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    recency_score: float = Field(ge=0.0, le=1.0)
    applicability_score: float = Field(ge=0.0, le=1.0)
    total_score: float
    matched_terms: tuple[str, ...] = ()
    rationale: str = Field(min_length=1)


class LearningRecord(FrozenMemoryContract):
    learning_id: str = Field(min_length=1)
    source_memory_ids: tuple[str, ...] = Field(min_length=1)
    lesson: str = Field(min_length=1)
    success_count: int = Field(default=0, ge=0)
    failure_count: int = Field(default=0, ge=0)
    confidence: float = Field(ge=0.0, le=1.0)
    applicability: MemoryApplicability
    last_validated_at: datetime | None = None
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_sources(self) -> LearningRecord:
        if len(set(self.source_memory_ids)) != len(
            self.source_memory_ids
        ):
            raise ValueError(
                "source_memory_ids cannot contain duplicates."
            )
        return self
'@

Write-Utf8NoBom "forge\autonomous_memory\__init__.py" @'
"""Aerion Forge autonomous memory and learning contracts."""

from forge.autonomous_memory.errors import (
    AutonomousMemoryError,
    MemoryContractError,
    MemoryIdentifierError,
    MemoryPolicyError,
    MemoryRedactionError,
    MemoryScopeError,
    MemorySupersessionError,
)
from forge.autonomous_memory.identifiers import (
    deterministic_memory_identifier,
    learning_record_identifier,
    memory_observation_identifier,
    memory_provenance_identifier,
    memory_query_identifier,
    memory_record_identifier,
)
from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryMatch,
    MemoryObservation,
    MemoryProvenance,
    MemoryQuery,
    MemoryRecord,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
    MemoryConfidencePolicy,
    MemoryLimitPolicy,
    MemorySafetyPolicy,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    MemoryStatus,
    RetentionClass,
)

__all__ = [
    "ApplicabilityKind",
    "AutonomousMemoryError",
    "AutonomousMemoryPolicy",
    "LearningRecord",
    "MemoryApplicability",
    "MemoryConfidencePolicy",
    "MemoryContractError",
    "MemoryIdentifierError",
    "MemoryKind",
    "MemoryLimitPolicy",
    "MemoryMatch",
    "MemoryObservation",
    "MemoryPolicyError",
    "MemoryProvenance",
    "MemoryQuery",
    "MemoryRecord",
    "MemoryRedactionError",
    "MemorySafetyPolicy",
    "MemoryScopeError",
    "MemorySourceKind",
    "MemoryStatus",
    "MemorySupersessionError",
    "RetentionClass",
    "deterministic_memory_identifier",
    "learning_record_identifier",
    "memory_observation_identifier",
    "memory_provenance_identifier",
    "memory_query_identifier",
    "memory_record_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_memory_identifiers.py" @'
from forge.autonomous_memory.identifiers import (
    memory_observation_identifier,
    memory_record_identifier,
)


def test_memory_identifier_is_stable() -> None:
    first = memory_record_identifier(
        {
            "repository": "repo",
            "statement": "Fact",
        }
    )
    second = memory_record_identifier(
        {
            "statement": "Fact",
            "repository": "repo",
        }
    )

    assert first == second
    assert first.startswith("memory-record-")


def test_observation_identifier_has_prefix() -> None:
    result = memory_observation_identifier(
        {"source_reference": "source-1"}
    )

    assert result.startswith("memory-observation-")
'@

Write-Utf8NoBom "tests\test_autonomous_memory_states.py" @'
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemoryStatus,
)


def test_memory_enumerations_are_stable() -> None:
    assert MemoryKind.REPOSITORY_FACT.value == "repository_fact"
    assert MemoryStatus.SUPERSEDED.value == "superseded"
    assert (
        ApplicabilityKind.EXACT_REPOSITORY.value
        == "exact_repository"
    )
'@

Write-Utf8NoBom "tests\test_autonomous_memory_policies.py" @'
import pytest

from forge.autonomous_memory.errors import MemoryPolicyError
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
    MemorySafetyPolicy,
)


def test_default_policy_is_safe_and_bounded() -> None:
    policy = AutonomousMemoryPolicy()

    assert policy.safety.require_provenance
    assert policy.safety.reject_secrets
    assert not policy.safety.allow_tool_execution
    assert policy.limits.maximum_query_results == 20


def test_tool_execution_cannot_be_enabled() -> None:
    with pytest.raises(MemoryPolicyError):
        MemorySafetyPolicy(allow_tool_execution=True)


def test_repository_evidence_must_win() -> None:
    with pytest.raises(MemoryPolicyError):
        MemorySafetyPolicy(
            current_repository_evidence_wins=False
        )
'@

Write-Utf8NoBom "tests\test_autonomous_memory_models.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryObservation,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemorySourceKind,
    RetentionClass,
)


def applicability() -> MemoryApplicability:
    return MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository-scoped memory.",
    )


def test_fact_requires_evidence() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            memory_id="memory-1",
            memory_kind=MemoryKind.REPOSITORY_FACT,
            statement="Repository uses Python.",
            normalized_statement="repository uses python",
            confidence=0.9,
            repository_scope="repository",
            source_references=("source-1",),
            applicability=applicability(),
            retention_class=RetentionClass.PROJECT_LIFETIME,
        )


def test_memory_cannot_supersede_itself() -> None:
    with pytest.raises(ValidationError):
        MemoryRecord(
            memory_id="memory-1",
            memory_kind=MemoryKind.HYPOTHESIS,
            statement="Possible constraint.",
            normalized_statement="possible constraint",
            confidence=0.5,
            repository_scope="repository",
            source_references=("source-1",),
            applicability=applicability(),
            retention_class=RetentionClass.TEMPORARY,
            supersedes_memory_id="memory-1",
        )


def test_observation_rejects_duplicate_evidence() -> None:
    with pytest.raises(ValidationError):
        MemoryObservation(
            observation_id="observation-1",
            source_kind=MemorySourceKind.REPOSITORY,
            source_reference="file.py",
            repository_root="repository",
            repository_fingerprint="fingerprint-1",
            content="Observed repository fact.",
            evidence_references=("evidence-1", "evidence-1"),
        )


def test_learning_requires_unique_sources() -> None:
    with pytest.raises(ValidationError):
        LearningRecord(
            learning_id="learning-1",
            source_memory_ids=("memory-1", "memory-1"),
            lesson="Use validated rollback checkpoints.",
            confidence=0.8,
            applicability=applicability(),
        )
'@

Write-Host ""
Write-Host "M5.5 Package 0 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_memory_identifiers.py `
    .\tests\test_autonomous_memory_states.py `
    .\tests\test_autonomous_memory_policies.py `
    .\tests\test_autonomous_memory_models.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.5 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.5 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short