[CmdletBinding()]
param([string]$RepositoryRoot = "D:\Software Dev\Aerion Forge")

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    $FullPath = Join-Path $RepositoryRoot $Path
    New-Item -ItemType Directory -Path (Split-Path $FullPath -Parent) -Force | Out-Null
    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )
    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-Success {
    param([string]$Name)
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.5-autonomous-memory-learning"
$CurrentBranch = git branch --show-current
Assert-Success "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "Expected '$ExpectedBranch', found '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_memory\normalization.py" @'
"""Deterministic memory normalization."""

from __future__ import annotations

import re
import unicodedata


_WHITESPACE = re.compile(r"\s+")
_NON_WORD = re.compile(r"[^a-z0-9\s._:/-]+")


def normalize_statement(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold().strip()
    normalized = _NON_WORD.sub(" ", normalized)
    return _WHITESPACE.sub(" ", normalized).strip()


def normalize_tags(values: tuple[str, ...]) -> tuple[str, ...]:
    normalized = {
        normalize_statement(value).replace(" ", "-")
        for value in values
        if normalize_statement(value)
    }
    return tuple(sorted(normalized))


def normalize_scope(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        sorted(
            {
                value.strip().replace("\\", "/")
                for value in values
                if value.strip()
            }
        )
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\redaction.py" @'
"""Secret detection for memory ingestion."""

from __future__ import annotations

import re
from dataclasses import dataclass

from forge.autonomous_memory.errors import MemoryRedactionError


@dataclass(frozen=True, slots=True)
class RedactionResult:
    content: str
    detected_categories: tuple[str, ...]


_PATTERNS = (
    (
        "private_key",
        re.compile(
            r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
            re.IGNORECASE,
        ),
    ),
    (
        "bearer_token",
        re.compile(
            r"\bBearer\s+[A-Za-z0-9._~+/=-]{16,}",
            re.IGNORECASE,
        ),
    ),
    (
        "secret_assignment",
        re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?token|secret|password)"
            r"\s*[:=]\s*['\"]?([^\s'\";,]{8,})"
        ),
    ),
    (
        "github_token",
        re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    ),
    (
        "aws_access_key",
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    ),
)


def redact_prohibited_content(content: str) -> RedactionResult:
    redacted = content
    detected: list[str] = []

    for category, pattern in _PATTERNS:
        if pattern.search(redacted):
            detected.append(category)
            redacted = pattern.sub(
                f"[REDACTED:{category}]",
                redacted,
            )

    return RedactionResult(
        content=redacted,
        detected_categories=tuple(sorted(set(detected))),
    )


def assert_no_prohibited_content(content: str) -> None:
    result = redact_prohibited_content(content)
    if result.detected_categories:
        raise MemoryRedactionError(
            "Prohibited memory content detected: "
            + ", ".join(result.detected_categories)
        )
'@

Write-Utf8NoBom "forge\autonomous_memory\provenance.py" @'
"""Provenance and evidence digest creation."""

from __future__ import annotations

import hashlib
import json

from forge.autonomous_memory.identifiers import memory_provenance_identifier
from forge.autonomous_memory.models import MemoryObservation, MemoryProvenance


def evidence_digest(values: tuple[str, ...]) -> str:
    canonical = json.dumps(
        sorted(set(values)),
        separators=(",", ":"),
        ensure_ascii=True,
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def build_provenance(
    *,
    memory_id: str,
    observation: MemoryObservation,
    actor: str,
) -> MemoryProvenance:
    digest = evidence_digest(observation.evidence_references)
    payload = {
        "memory_id": memory_id,
        "source_kind": observation.source_kind.value,
        "source_reference": observation.source_reference,
        "repository_fingerprint": observation.repository_fingerprint,
        "evidence_digest": digest,
        "actor": actor,
    }

    return MemoryProvenance(
        provenance_id=memory_provenance_identifier(payload),
        memory_id=memory_id,
        source_kind=observation.source_kind,
        source_reference=observation.source_reference,
        evidence_digest=digest,
        repository_fingerprint=observation.repository_fingerprint,
        actor=actor,
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\classification.py" @'
"""Rule-based memory classification."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.normalization import normalize_statement
from forge.autonomous_memory.states import MemoryKind


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    memory_kind: MemoryKind
    rationale: str


_RULES = (
    (("failed", "failure", "regression", "error"), MemoryKind.FAILURE_PATTERN),
    (("rollback", "recovered", "recovery"), MemoryKind.RECOVERY_PATTERN),
    (("validation passed", "tests passed"), MemoryKind.VALIDATION_OUTCOME),
    (("execution completed", "execution succeeded"), MemoryKind.EXECUTION_OUTCOME),
    (("architecture", "must not", "constraint"), MemoryKind.ARCHITECTURE_CONSTRAINT),
    (("business rule", "customer requires"), MemoryKind.BUSINESS_RULE),
    (("decision", "selected"), MemoryKind.IMPLEMENTATION_DECISION),
    (("lesson", "best practice"), MemoryKind.ENGINEERING_LESSON),
    (("prefer", "preference"), MemoryKind.USER_PREFERENCE),
    (("maybe", "possibly", "hypothesis", "suspect"), MemoryKind.HYPOTHESIS),
)


def classify_observation(
    observation: MemoryObservation,
) -> ClassificationResult:
    normalized = normalize_statement(observation.content)

    for terms, memory_kind in _RULES:
        if any(term in normalized for term in terms):
            return ClassificationResult(
                memory_kind=memory_kind,
                rationale=f"Matched rules for {memory_kind.value}.",
            )

    if observation.evidence_references:
        return ClassificationResult(
            memory_kind=MemoryKind.REPOSITORY_FACT,
            rationale="Evidence-backed observation.",
        )

    return ClassificationResult(
        memory_kind=MemoryKind.HYPOTHESIS,
        rationale="Observation lacks supporting evidence.",
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\confidence.py" @'
"""Initial confidence assessment."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.states import MemoryKind, MemorySourceKind


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    score: float
    factors: tuple[str, ...]


_BASE = {
    MemorySourceKind.REPOSITORY: 0.80,
    MemorySourceKind.VALIDATION: 0.85,
    MemorySourceKind.EXECUTION: 0.75,
    MemorySourceKind.DECISION: 0.70,
    MemorySourceKind.MISSION: 0.65,
    MemorySourceKind.SESSION: 0.60,
    MemorySourceKind.ARCHITECTURE_REVIEW: 0.80,
    MemorySourceKind.HUMAN_CORRECTION: 0.75,
}


def assess_initial_confidence(
    *,
    observation: MemoryObservation,
    memory_kind: MemoryKind,
) -> ConfidenceAssessment:
    score = _BASE[observation.source_kind]
    factors = [f"source={observation.source_kind.value}"]

    if observation.evidence_references:
        score += min(
            0.15,
            len(observation.evidence_references) * 0.03,
        )
        factors.append(
            f"evidence_count={len(observation.evidence_references)}"
        )
    else:
        score -= 0.20
        factors.append("no_evidence")

    if memory_kind is MemoryKind.HYPOTHESIS:
        score = min(score, 0.60)
        factors.append("hypothesis_cap")

    return ConfidenceAssessment(
        score=round(max(0.0, min(score, 1.0)), 6),
        factors=tuple(factors),
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\deduplication.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_memory\ingestion.py" @'
"""Memory observation ingestion service."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.classification import (
    ClassificationResult,
    classify_observation,
)
from forge.autonomous_memory.confidence import (
    ConfidenceAssessment,
    assess_initial_confidence,
)
from forge.autonomous_memory.errors import (
    MemoryContractError,
    MemoryRedactionError,
)
from forge.autonomous_memory.identifiers import memory_record_identifier
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryObservation,
    MemoryProvenance,
    MemoryRecord,
)
from forge.autonomous_memory.normalization import (
    normalize_scope,
    normalize_statement,
    normalize_tags,
)
from forge.autonomous_memory.policies import AutonomousMemoryPolicy
from forge.autonomous_memory.provenance import build_provenance
from forge.autonomous_memory.redaction import redact_prohibited_content
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


@dataclass(frozen=True, slots=True)
class IngestionResult:
    record: MemoryRecord
    provenance: MemoryProvenance
    classification: ClassificationResult
    confidence: ConfidenceAssessment


@dataclass(frozen=True, slots=True)
class MemoryIngestionService:
    policy: AutonomousMemoryPolicy

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
        if not actor.strip():
            raise MemoryContractError("Actor cannot be empty.")

        if (
            len(observation.content)
            > self.policy.limits.maximum_observation_characters
        ):
            raise MemoryContractError(
                "Observation exceeds configured size limit."
            )

        if len(observation.tags) > self.policy.limits.maximum_tags:
            raise MemoryContractError(
                "Observation exceeds configured tag limit."
            )

        redaction = redact_prohibited_content(observation.content)

        if (
            self.policy.safety.reject_secrets
            and redaction.detected_categories
        ):
            raise MemoryRedactionError(
                "Prohibited content detected: "
                + ", ".join(redaction.detected_categories)
            )

        normalized = normalize_statement(redaction.content)
        if not normalized:
            raise MemoryContractError(
                "Normalized statement cannot be empty."
            )

        classification = (
            ClassificationResult(
                memory_kind=memory_kind,
                rationale="Memory kind supplied explicitly.",
            )
            if memory_kind is not None
            else classify_observation(observation)
        )

        confidence = assess_initial_confidence(
            observation=observation,
            memory_kind=classification.memory_kind,
        )

        if (
            classification.memory_kind
            is MemoryKind.REPOSITORY_FACT
            and confidence.score
            < self.policy.confidence.minimum_fact_confidence
        ):
            classification = ClassificationResult(
                memory_kind=MemoryKind.HYPOTHESIS,
                rationale=(
                    "Fact confidence below policy threshold."
                ),
            )
            confidence = assess_initial_confidence(
                observation=observation,
                memory_kind=MemoryKind.HYPOTHESIS,
            )

        memory_id = memory_record_identifier(
            {
                "repository_scope": observation.repository_root,
                "memory_kind": classification.memory_kind.value,
                "normalized_statement": normalized,
                "source_reference": observation.source_reference,
                "repository_fingerprint": (
                    observation.repository_fingerprint
                ),
            }
        )

        applicability = MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope=observation.repository_root,
            module_scope=normalize_scope(module_scope),
            capability_scope=normalize_scope(capability_scope),
            business_domain=business_domain,
            rationale="Repository-scoped by default.",
        )

        record = MemoryRecord(
            memory_id=memory_id,
            memory_kind=classification.memory_kind,
            statement=redaction.content.strip(),
            normalized_statement=normalized,
            confidence=confidence.score,
            repository_scope=observation.repository_root,
            module_scope=normalize_scope(module_scope),
            capability_scope=normalize_scope(capability_scope),
            business_domain=business_domain,
            evidence_references=tuple(
                sorted(set(observation.evidence_references))
            ),
            source_references=(observation.source_reference,),
            tags=normalize_tags(observation.tags),
            applicability=applicability,
            retention_class=_retention_for_kind(
                classification.memory_kind
            ),
        )

        provenance = build_provenance(
            memory_id=memory_id,
            observation=observation,
            actor=actor.strip(),
        )

        return IngestionResult(
            record=record,
            provenance=provenance,
            classification=classification,
            confidence=confidence,
        )


def _retention_for_kind(
    memory_kind: MemoryKind,
) -> RetentionClass:
    if memory_kind in {
        MemoryKind.ARCHITECTURE_CONSTRAINT,
        MemoryKind.BUSINESS_RULE,
    }:
        return RetentionClass.PERMANENT

    if memory_kind in {
        MemoryKind.ENGINEERING_LESSON,
        MemoryKind.FAILURE_PATTERN,
        MemoryKind.RECOVERY_PATTERN,
        MemoryKind.NEGATIVE_EVIDENCE,
    }:
        return RetentionClass.LONG_LIVED

    if memory_kind is MemoryKind.HYPOTHESIS:
        return RetentionClass.TEMPORARY

    return RetentionClass.PROJECT_LIFETIME
'@

Write-Utf8NoBom "tests\test_autonomous_memory_normalization.py" @'
from forge.autonomous_memory.normalization import (
    normalize_scope,
    normalize_statement,
    normalize_tags,
)


def test_statement_normalization() -> None:
    assert (
        normalize_statement("  Repository   Uses Python! ")
        == "repository uses python"
    )


def test_tags_are_normalized() -> None:
    assert normalize_tags(
        ("Architecture", "architecture", "Safe Change")
    ) == ("architecture", "safe-change")


def test_scope_uses_forward_slashes() -> None:
    assert normalize_scope(
        ("forge\\planning", "forge/planning")
    ) == ("forge/planning",)
'@

Write-Utf8NoBom "tests\test_autonomous_memory_redaction.py" @'
import pytest

from forge.autonomous_memory.errors import MemoryRedactionError
from forge.autonomous_memory.redaction import (
    assert_no_prohibited_content,
    redact_prohibited_content,
)


def test_secret_is_redacted() -> None:
    result = redact_prohibited_content(
        "api_key=abcdefghijklmnop"
    )
    assert "REDACTED" in result.content


def test_secret_assertion_rejects() -> None:
    with pytest.raises(MemoryRedactionError):
        assert_no_prohibited_content(
            "password=supersecretvalue"
        )
'@

Write-Utf8NoBom "tests\test_autonomous_memory_provenance.py" @'
from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.provenance import (
    build_provenance,
    evidence_digest,
)
from forge.autonomous_memory.states import MemorySourceKind


def observation() -> MemoryObservation:
    return MemoryObservation(
        observation_id="observation-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="forge/module.py",
        repository_root="repository",
        repository_fingerprint="fingerprint-1",
        content="Repository fact.",
        evidence_references=("evidence-2", "evidence-1"),
    )


def test_digest_is_order_independent() -> None:
    assert evidence_digest(
        ("evidence-1", "evidence-2")
    ) == evidence_digest(
        ("evidence-2", "evidence-1")
    )


def test_provenance_is_created() -> None:
    result = build_provenance(
        memory_id="memory-1",
        observation=observation(),
        actor="Aerion",
    )
    assert result.memory_id == "memory-1"
'@

Write-Utf8NoBom "tests\test_autonomous_memory_classification.py" @'
from forge.autonomous_memory.classification import classify_observation
from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.states import (
    MemoryKind,
    MemorySourceKind,
)


def make_observation(
    content: str,
    evidence: tuple[str, ...] = (),
) -> MemoryObservation:
    return MemoryObservation(
        observation_id="observation-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="source-1",
        repository_root="repository",
        repository_fingerprint="fingerprint-1",
        content=content,
        evidence_references=evidence,
    )


def test_failure_is_classified() -> None:
    result = classify_observation(
        make_observation("Validation failed after deployment.")
    )
    assert result.memory_kind is MemoryKind.FAILURE_PATTERN


def test_evidence_backed_default_is_fact() -> None:
    result = classify_observation(
        make_observation(
            "Repository uses Python.",
            ("evidence-1",),
        )
    )
    assert result.memory_kind is MemoryKind.REPOSITORY_FACT
'@

Write-Utf8NoBom "tests\test_autonomous_memory_deduplication.py" @'
from forge.autonomous_memory.deduplication import deduplicate_records
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def record(memory_id: str) -> MemoryRecord:
    applicability = MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository scoped.",
    )
    return MemoryRecord(
        memory_id=memory_id,
        memory_kind=MemoryKind.REPOSITORY_FACT,
        statement="Repository uses Python.",
        normalized_statement="repository uses python",
        confidence=0.9,
        repository_scope="repository",
        evidence_references=("evidence-1",),
        source_references=("source-1",),
        applicability=applicability,
        retention_class=RetentionClass.PROJECT_LIFETIME,
    )


def test_exact_duplicates_are_removed() -> None:
    result = deduplicate_records(
        (record("memory-2"), record("memory-1"))
    )
    assert len(result.records) == 1
    assert result.duplicate_memory_ids == ("memory-2",)
'@

Write-Utf8NoBom "tests\test_autonomous_memory_ingestion.py" @'
import pytest

from forge.autonomous_memory.errors import MemoryRedactionError
from forge.autonomous_memory.ingestion import MemoryIngestionService
from forge.autonomous_memory.models import MemoryObservation
from forge.autonomous_memory.policies import AutonomousMemoryPolicy
from forge.autonomous_memory.states import (
    MemoryKind,
    MemorySourceKind,
)


def observation(
    content: str,
    evidence: tuple[str, ...] = ("evidence-1",),
) -> MemoryObservation:
    return MemoryObservation(
        observation_id="observation-1",
        source_kind=MemorySourceKind.REPOSITORY,
        source_reference="forge/module.py",
        repository_root="repository",
        repository_fingerprint="fingerprint-1",
        content=content,
        evidence_references=evidence,
        tags=("Architecture", "architecture"),
    )


def test_ingestion_creates_record_and_provenance() -> None:
    service = MemoryIngestionService(
        policy=AutonomousMemoryPolicy()
    )
    result = service.ingest(
        observation("Repository uses Python."),
        actor="Aerion",
        module_scope=("forge\\module.py",),
    )
    assert result.record.memory_kind is MemoryKind.REPOSITORY_FACT
    assert result.record.module_scope == ("forge/module.py",)
    assert result.record.tags == ("architecture",)
    assert result.provenance.memory_id == result.record.memory_id


def test_without_evidence_remains_hypothesis() -> None:
    service = MemoryIngestionService(
        policy=AutonomousMemoryPolicy()
    )
    result = service.ingest(
        observation("Repository may use another runtime.", ()),
        actor="Aerion",
    )
    assert result.record.memory_kind is MemoryKind.HYPOTHESIS


def test_ingestion_rejects_secret() -> None:
    service = MemoryIngestionService(
        policy=AutonomousMemoryPolicy()
    )
    with pytest.raises(MemoryRedactionError):
        service.ingest(
            observation("api_key=abcdefghijklmnop"),
            actor="Aerion",
        )
'@

Write-Host ""
Write-Host "M5.5 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-Success "Ruff fix"

python -m ruff check .
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_memory_normalization.py `
    .\tests\test_autonomous_memory_redaction.py `
    .\tests\test_autonomous_memory_provenance.py `
    .\tests\test_autonomous_memory_classification.py `
    .\tests\test_autonomous_memory_deduplication.py `
    .\tests\test_autonomous_memory_ingestion.py `
    -p no:cacheprovider
Assert-Success "M5.5 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full test suite"

Write-Host ""
Write-Host "M5.5 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
