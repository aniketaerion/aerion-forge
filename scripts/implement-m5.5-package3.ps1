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
    throw "M5.5 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_memory\supersession.py" @'
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
'@

Write-Utf8NoBom "forge\autonomous_memory\feedback.py" @'
"""Outcome feedback contracts and attribution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class FeedbackOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"


@dataclass(frozen=True, slots=True)
class MemoryFeedback:
    """Validated outcome attributed to reused memory."""

    feedback_id: str
    memory_id: str
    mission_id: str
    outcome: FeedbackOutcome
    validated: bool
    evidence_references: tuple[str, ...]
    rationale: str


def assert_feedback_is_usable(
    feedback: MemoryFeedback,
) -> None:
    """Require validated feedback and evidence."""
    if not feedback.validated:
        raise ValueError(
            "Only validated feedback may update learning."
        )

    if not feedback.evidence_references:
        raise ValueError(
            "Validated feedback requires evidence."
        )
'@

Write-Utf8NoBom "forge\autonomous_memory\learning.py" @'
"""Learning-record creation and feedback updates."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
    assert_feedback_is_usable,
)
from forge.autonomous_memory.identifiers import (
    learning_record_identifier,
)
from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryRecord,
)


@dataclass(frozen=True, slots=True)
class LearningUpdate:
    """Updated learning record and attribution summary."""

    learning: LearningRecord
    feedback: MemoryFeedback


def create_learning_record(
    *,
    lesson: str,
    source_records: tuple[MemoryRecord, ...],
    applicability: MemoryApplicability,
    confidence: float,
) -> LearningRecord:
    """Create evidence-backed learning from source memories."""
    if not source_records:
        raise ValueError(
            "Learning requires at least one source memory."
        )

    source_ids = tuple(
        sorted(
            {
                record.memory_id
                for record in source_records
            }
        )
    )

    payload = {
        "lesson": lesson,
        "source_memory_ids": source_ids,
        "repository_scope": applicability.repository_scope,
    }

    return LearningRecord(
        learning_id=learning_record_identifier(payload),
        source_memory_ids=source_ids,
        lesson=lesson,
        success_count=0,
        failure_count=0,
        confidence=confidence,
        applicability=applicability,
    )


def apply_feedback(
    *,
    learning: LearningRecord,
    feedback: MemoryFeedback,
) -> LearningUpdate:
    """Update success/failure counts and confidence."""
    assert_feedback_is_usable(feedback)

    success_count = learning.success_count
    failure_count = learning.failure_count

    if feedback.outcome is FeedbackOutcome.SUCCESS:
        success_count += 1
    else:
        failure_count += 1

    total = success_count + failure_count
    empirical = (
        success_count / total
        if total
        else learning.confidence
    )

    confidence = round(
        max(
            0.0,
            min(
                1.0,
                0.5 * learning.confidence
                + 0.5 * empirical,
            ),
        ),
        6,
    )

    updated = learning.model_copy(
        update={
            "success_count": success_count,
            "failure_count": failure_count,
            "confidence": confidence,
        }
    )

    return LearningUpdate(
        learning=updated,
        feedback=feedback,
    )
'@

Write-Utf8NoBom "forge\autonomous_memory\consolidation.py" @'
"""Deterministic memory consolidation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.models import MemoryRecord


@dataclass(frozen=True, slots=True)
class ConsolidationGroup:
    """Group of semantically identical memory records."""

    canonical: MemoryRecord
    members: tuple[MemoryRecord, ...]


def consolidate_records(
    records: tuple[MemoryRecord, ...],
) -> tuple[ConsolidationGroup, ...]:
    """Group exact semantic duplicates without deleting history."""
    groups: dict[
        tuple[str, str, str],
        list[MemoryRecord],
    ] = {}

    for record in records:
        key = (
            record.repository_scope,
            record.memory_kind.value,
            record.normalized_statement,
        )
        groups.setdefault(key, []).append(record)

    consolidated: list[ConsolidationGroup] = []

    for key in sorted(groups):
        members = tuple(
            sorted(
                groups[key],
                key=lambda item: (
                    -item.confidence,
                    item.memory_id,
                ),
            )
        )
        consolidated.append(
            ConsolidationGroup(
                canonical=members[0],
                members=members,
            )
        )

    return tuple(consolidated)
'@

Write-Utf8NoBom "forge\autonomous_memory\learning_service.py" @'
"""Application service for autonomous memory learning."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_memory.feedback import MemoryFeedback
from forge.autonomous_memory.learning import (
    LearningUpdate,
    apply_feedback,
    create_learning_record,
)
from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.storage import MemoryStorage


@dataclass(slots=True)
class AutonomousLearningService:
    """Create and update learning records."""

    storage: MemoryStorage

    def create(
        self,
        *,
        lesson: str,
        source_records: tuple[MemoryRecord, ...],
        applicability: MemoryApplicability,
        confidence: float,
    ) -> LearningRecord:
        learning = create_learning_record(
            lesson=lesson,
            source_records=source_records,
            applicability=applicability,
            confidence=confidence,
        )
        self.storage.put_learning(learning)
        return learning

    def apply_feedback(
        self,
        *,
        learning: LearningRecord,
        feedback: MemoryFeedback,
    ) -> LearningUpdate:
        update = apply_feedback(
            learning=learning,
            feedback=feedback,
        )
        self.storage.put_learning(update.learning)
        return update
'@

Write-Utf8NoBom "tests\test_autonomous_memory_supersession.py" @'
import pytest

from forge.autonomous_memory.errors import (
    MemorySupersessionError,
)
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    MemoryStatus,
    RetentionClass,
)
from forge.autonomous_memory.supersession import (
    apply_supersession,
)


def record(
    memory_id: str,
    *,
    supersedes: str | None = None,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=0.5,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
        supersedes_memory_id=supersedes,
    )


def test_supersession_preserves_history() -> None:
    previous = record("memory-1")
    replacement = record(
        "memory-2",
        supersedes="memory-1",
    )

    result = apply_supersession(
        previous=previous,
        replacement=replacement,
        existing_records=(previous,),
    )

    assert (
        result.superseded.status
        is MemoryStatus.SUPERSEDED
    )
    assert result.replacement.memory_id == "memory-2"


def test_cross_repository_supersession_is_rejected() -> None:
    previous = record("memory-1")
    replacement = record(
        "memory-2",
        supersedes="memory-1",
    ).model_copy(
        update={"repository_scope": "other"}
    )

    with pytest.raises(MemorySupersessionError):
        apply_supersession(
            previous=previous,
            replacement=replacement,
            existing_records=(previous,),
        )
'@

Write-Utf8NoBom "tests\test_autonomous_memory_feedback.py" @'
import pytest

from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
    assert_feedback_is_usable,
)


def test_validated_feedback_requires_evidence() -> None:
    feedback = MemoryFeedback(
        feedback_id="feedback-1",
        memory_id="memory-1",
        mission_id="mission-1",
        outcome=FeedbackOutcome.SUCCESS,
        validated=True,
        evidence_references=(),
        rationale="Mission succeeded.",
    )

    with pytest.raises(ValueError):
        assert_feedback_is_usable(feedback)
'@

Write-Utf8NoBom "tests\test_autonomous_memory_learning.py" @'
from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
)
from forge.autonomous_memory.learning import (
    apply_feedback,
    create_learning_record,
)
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def applicability() -> MemoryApplicability:
    return MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository scoped.",
    )


def record() -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.ENGINEERING_LESSON,
        statement="Use rollback checkpoints.",
        normalized_statement="use rollback checkpoints",
        confidence=0.8,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=applicability(),
        retention_class=RetentionClass.LONG_LIVED,
    )


def test_feedback_updates_learning_counts() -> None:
    learning = create_learning_record(
        lesson="Use rollback checkpoints.",
        source_records=(record(),),
        applicability=applicability(),
        confidence=0.8,
    )
    feedback = MemoryFeedback(
        feedback_id="feedback-1",
        memory_id="memory-1",
        mission_id="mission-1",
        outcome=FeedbackOutcome.SUCCESS,
        validated=True,
        evidence_references=("evidence-1",),
        rationale="Rollback succeeded.",
    )

    result = apply_feedback(
        learning=learning,
        feedback=feedback,
    )

    assert result.learning.success_count == 1
    assert result.learning.failure_count == 0
'@

Write-Utf8NoBom "tests\test_autonomous_memory_consolidation.py" @'
from forge.autonomous_memory.consolidation import (
    consolidate_records,
)
from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def record(
    memory_id: str,
    confidence: float,
) -> MemoryRecord:
    return MemoryRecord(
        memory_id=memory_id,
        memory_kind=MemoryKind.HYPOTHESIS,
        statement="Possible constraint.",
        normalized_statement="possible constraint",
        confidence=confidence,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.TEMPORARY,
    )


def test_highest_confidence_record_is_canonical() -> None:
    groups = consolidate_records(
        (
            record("memory-1", 0.5),
            record("memory-2", 0.8),
        )
    )

    assert len(groups) == 1
    assert groups[0].canonical.memory_id == "memory-2"
    assert len(groups[0].members) == 2
'@

Write-Utf8NoBom "tests\test_autonomous_memory_learning_service.py" @'
from forge.autonomous_memory.feedback import (
    FeedbackOutcome,
    MemoryFeedback,
)
from forge.autonomous_memory.learning_service import (
    AutonomousLearningService,
)
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


def test_learning_service_persists_learning() -> None:
    storage = InMemoryMemoryStorage()
    service = AutonomousLearningService(storage=storage)
    applicability = MemoryApplicability(
        kind=ApplicabilityKind.EXACT_REPOSITORY,
        repository_scope="repository",
        rationale="Repository scoped.",
    )
    record = MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.ENGINEERING_LESSON,
        statement="Use rollback checkpoints.",
        normalized_statement="use rollback checkpoints",
        confidence=0.8,
        repository_scope="repository",
        source_references=("source-1",),
        applicability=applicability,
        retention_class=RetentionClass.LONG_LIVED,
    )

    learning = service.create(
        lesson="Use rollback checkpoints.",
        source_records=(record,),
        applicability=applicability,
        confidence=0.8,
    )

    update = service.apply_feedback(
        learning=learning,
        feedback=MemoryFeedback(
            feedback_id="feedback-1",
            memory_id="memory-1",
            mission_id="mission-1",
            outcome=FeedbackOutcome.SUCCESS,
            validated=True,
            evidence_references=("evidence-1",),
            rationale="Rollback succeeded.",
        ),
    )

    assert update.learning.success_count == 1
    assert storage.all_learning()[0].success_count == 1
'@

Write-Host ""
Write-Host "M5.5 Package 3 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_memory_supersession.py `
    .\tests\test_autonomous_memory_feedback.py `
    .\tests\test_autonomous_memory_learning.py `
    .\tests\test_autonomous_memory_consolidation.py `
    .\tests\test_autonomous_memory_learning_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.5 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.5 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short