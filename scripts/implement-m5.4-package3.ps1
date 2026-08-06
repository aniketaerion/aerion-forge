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

$ExpectedBranch = "feature/m5.4-autonomous-decision-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.4 Package 3 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_decision\selector.py" @'
"""Deterministic decision selection."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)
from forge.autonomous_decision.ranking import (
    RankedCandidate,
    rank_candidates,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    DecisionDisposition,
)


@dataclass(frozen=True, slots=True)
class SelectionResult:
    """Result of deterministic candidate selection."""

    selected: RankedCandidate | None
    ranked: tuple[RankedCandidate, ...]
    disposition: DecisionDisposition


def disposition_for_candidate(
    candidate: CandidateAction,
) -> DecisionDisposition:
    """Map one candidate action to a committed disposition."""
    mapping = {
        CandidateActionKind.EXECUTE_NEXT_STEP: (
            DecisionDisposition.SELECT_ACTION
        ),
        CandidateActionKind.RETRY_CURRENT_STEP: (
            DecisionDisposition.RETRY
        ),
        CandidateActionKind.ROLLBACK_CURRENT_STEP: (
            DecisionDisposition.ROLLBACK
        ),
        CandidateActionKind.REPLAN_REMAINING_WORK: (
            DecisionDisposition.REPLAN
        ),
        CandidateActionKind.REQUEST_APPROVAL: (
            DecisionDisposition.PAUSE
        ),
        CandidateActionKind.PAUSE_MISSION: (
            DecisionDisposition.PAUSE
        ),
        CandidateActionKind.ESCALATE_MISSION: (
            DecisionDisposition.ESCALATE
        ),
        CandidateActionKind.COMPLETE_MISSION: (
            DecisionDisposition.COMPLETE
        ),
        CandidateActionKind.CANCEL_MISSION: (
            DecisionDisposition.CANCEL
        ),
    }

    return mapping[candidate.action_kind]


def select_candidate(
    candidates: tuple[CandidateAction, ...],
    assessments: tuple[CandidateAssessment, ...],
) -> SelectionResult:
    """Select at most one accepted candidate."""
    ranked = rank_candidates(candidates, assessments)

    if not ranked:
        return SelectionResult(
            selected=None,
            ranked=(),
            disposition=DecisionDisposition.NO_SAFE_ACTION,
        )

    selected = ranked[0]

    return SelectionResult(
        selected=selected,
        ranked=ranked,
        disposition=disposition_for_candidate(
            selected.candidate
        ),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\rationale.py" @'
"""Structured decision rationale generation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
)
from forge.autonomous_decision.ranking import RankedCandidate
from forge.autonomous_decision.states import DecisionDisposition


@dataclass(frozen=True, slots=True)
class DecisionRationale:
    """Human-readable and structured decision explanation."""

    summary: str
    factors: tuple[str, ...]
    rejected_alternatives: tuple[str, ...]


def build_rationale(
    *,
    context: DecisionContext,
    disposition: DecisionDisposition,
    selected: RankedCandidate | None,
    assessments: tuple[CandidateAssessment, ...],
) -> DecisionRationale:
    """Build deterministic rationale from assessments."""
    rejected = tuple(
        sorted(
            assessment.candidate_id
            for assessment in assessments
            if assessment.rejection_reasons
        )
    )

    if selected is None:
        return DecisionRationale(
            summary=(
                "No candidate satisfied feasibility, policy, "
                "risk, confidence, evidence, and utility constraints."
            ),
            factors=(
                f"context={context.context_id}",
                f"disposition={disposition.value}",
                f"rejected_candidates={len(rejected)}",
            ),
            rejected_alternatives=rejected,
        )

    assessment = selected.assessment

    factors = (
        f"context={context.context_id}",
        f"candidate={selected.candidate.candidate_id}",
        f"rank={selected.rank}",
        f"total_score={assessment.total_score:.6f}",
        f"risk={assessment.risk_score:.6f}",
        f"confidence={assessment.confidence_score:.6f}",
        f"evidence={assessment.evidence_score:.6f}",
        f"utility={assessment.utility_score:.6f}",
        f"reversibility={assessment.reversibility_score:.6f}",
    )

    return DecisionRationale(
        summary=(
            f"Selected {selected.candidate.action_kind.value} "
            f"for candidate {selected.candidate.candidate_id}."
        ),
        factors=factors,
        rejected_alternatives=rejected,
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\replay_guard.py" @'
"""Context-bound decision replay protection."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_decision.errors import DecisionReplayError
from forge.autonomous_decision.models import DecisionRecord


@dataclass(slots=True)
class DecisionReplayGuard:
    """Prevent conflicting committed decisions for one context."""

    _records_by_fingerprint: dict[str, DecisionRecord] = field(
        default_factory=dict
    )

    def check_and_record(
        self,
        record: DecisionRecord,
    ) -> DecisionRecord:
        """Accept identical replay and reject conflicting replay."""
        existing = self._records_by_fingerprint.get(
            record.context_fingerprint
        )

        if existing is None:
            self._records_by_fingerprint[
                record.context_fingerprint
            ] = record
            return record

        if existing == record:
            return existing

        raise DecisionReplayError(
            "Conflicting committed decision for context "
            f"{record.context_fingerprint}."
        )

    def get(
        self,
        context_fingerprint: str,
    ) -> DecisionRecord | None:
        return self._records_by_fingerprint.get(
            context_fingerprint
        )
'@

Write-Utf8NoBom "forge\autonomous_decision\decision_journal.py" @'
"""Append-only decision journal."""

from __future__ import annotations

from dataclasses import dataclass, field

from forge.autonomous_decision.errors import DecisionContractError
from forge.autonomous_decision.models import DecisionRecord


@dataclass(slots=True)
class InMemoryDecisionJournal:
    """Deterministic append-only journal for committed decisions."""

    _records: list[DecisionRecord] = field(default_factory=list)

    def append(self, record: DecisionRecord) -> None:
        if any(
            existing.decision_id == record.decision_id
            for existing in self._records
        ):
            raise DecisionContractError(
                f"Duplicate decision record: {record.decision_id}"
            )

        self._records.append(record)

    def records_for_request(
        self,
        request_id: str,
    ) -> tuple[DecisionRecord, ...]:
        return tuple(
            record
            for record in self._records
            if record.request_id == request_id
        )

    def all_records(self) -> tuple[DecisionRecord, ...]:
        return tuple(self._records)
'@

Write-Utf8NoBom "forge\autonomous_decision\context_fingerprint.py" @'
"""Stable fingerprints for evaluated decision contexts."""

from __future__ import annotations

import hashlib
import json

from forge.autonomous_decision.models import DecisionContext


def decision_context_fingerprint(
    context: DecisionContext,
) -> str:
    """Return a stable fingerprint for one decision context."""
    payload = context.model_dump(mode="json")
    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )

    return hashlib.sha256(
        canonical.encode("utf-8")
    ).hexdigest()
'@

Write-Utf8NoBom "forge\autonomous_decision\decision_service.py" @'
"""Application service for one complete autonomous decision."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.assessment_service import (
    CandidateAssessmentService,
)
from forge.autonomous_decision.candidate_service import (
    CandidatePreparationService,
)
from forge.autonomous_decision.context_fingerprint import (
    decision_context_fingerprint,
)
from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.identifiers import (
    decision_record_identifier,
    decision_stop_identifier,
)
from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
    DecisionRecord,
    DecisionRequest,
    DecisionStop,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.rationale import (
    DecisionRationale,
    build_rationale,
)
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.selector import (
    SelectionResult,
    select_candidate,
)
from forge.autonomous_decision.states import (
    DecisionDisposition,
    DecisionStopKind,
)


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Complete M5.4 decision result."""

    record: DecisionRecord
    stop: DecisionStop | None
    selection: SelectionResult
    rationale: DecisionRationale
    assessments: tuple[CandidateAssessment, ...]


@dataclass(slots=True)
class AutonomousDecisionService:
    """Generate, assess, select, journal, and replay-guard decisions."""

    policy: AutonomousDecisionPolicy
    journal: InMemoryDecisionJournal
    replay_guard: DecisionReplayGuard

    def decide(
        self,
        request: DecisionRequest,
        context: DecisionContext,
    ) -> DecisionResult:
        preparation = CandidatePreparationService(
            policy=self.policy
        ).prepare(request, context)

        assessor = CandidateAssessmentService(
            policy=self.policy
        )
        assessments = tuple(
            assessor.assess(item, context)
            for item in preparation.prepared
        )

        candidates = tuple(
            item.candidate
            for item in preparation.prepared
        )
        selection = select_candidate(
            candidates,
            assessments,
        )

        rationale = build_rationale(
            context=context,
            disposition=selection.disposition,
            selected=selection.selected,
            assessments=assessments,
        )

        fingerprint = decision_context_fingerprint(context)
        selected_candidate_id = (
            selection.selected.candidate.candidate_id
            if selection.selected is not None
            else None
        )
        selected_assessment = (
            selection.selected.assessment
            if selection.selected is not None
            else None
        )

        payload = {
            "request_id": request.request_id,
            "context_id": context.context_id,
            "context_fingerprint": fingerprint,
            "selected_candidate_id": selected_candidate_id,
            "disposition": selection.disposition.value,
        }

        record = DecisionRecord(
            decision_id=decision_record_identifier(payload),
            request_id=request.request_id,
            context_id=context.context_id,
            selected_candidate_id=selected_candidate_id,
            decision_kind=request.decision_kind,
            disposition=selection.disposition,
            rationale=rationale.summary,
            alternative_candidate_ids=tuple(
                ranked.candidate.candidate_id
                for ranked in selection.ranked[1:]
            ),
            rejected_candidate_ids=tuple(
                sorted(
                    assessment.candidate_id
                    for assessment in assessments
                    if assessment.rejection_reasons
                )
            ),
            assessment_ids=tuple(
                assessment.assessment_id
                for assessment in assessments
            ),
            evidence_references=context.evidence_references,
            approval_required=(
                selection.selected.candidate.approval_required
                if selection.selected is not None
                else False
            ),
            confidence=(
                selected_assessment.confidence_score
                if selected_assessment is not None
                else 0.0
            ),
            context_fingerprint=fingerprint,
        )

        committed = self.replay_guard.check_and_record(record)

        if committed.decision_id not in {
            item.decision_id
            for item in self.journal.all_records()
        }:
            self.journal.append(committed)

        stop = None

        if (
            selection.disposition
            is DecisionDisposition.NO_SAFE_ACTION
        ):
            stop = DecisionStop(
                stop_id=decision_stop_identifier(
                    {
                        "request_id": request.request_id,
                        "context_fingerprint": fingerprint,
                        "stop_kind": (
                            DecisionStopKind.NO_SAFE_ACTION.value
                        ),
                    }
                ),
                request_id=request.request_id,
                stop_kind=DecisionStopKind.NO_SAFE_ACTION,
                reason=rationale.summary,
                resumable=True,
                evidence_references=context.evidence_references,
            )

        return DecisionResult(
            record=committed,
            stop=stop,
            selection=selection,
            rationale=rationale,
            assessments=assessments,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_selector.py" @'
from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)
from forge.autonomous_decision.selector import select_candidate
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
    DecisionDisposition,
)


def candidate(candidate_id: str) -> CandidateAction:
    return CandidateAction(
        candidate_id=candidate_id,
        action_kind=CandidateActionKind.EXECUTE_NEXT_STEP,
        target_step_id="step-1",
        description="Execute step.",
        required_authority="a2_modify",
        risk_class="medium",
        evidence_references=("evidence-1",),
        source=CandidateSource.APPROVED_PLAN,
    )


def assessment(
    assessment_id: str,
    candidate_id: str,
    total_score: float,
) -> CandidateAssessment:
    return CandidateAssessment(
        assessment_id=assessment_id,
        candidate_id=candidate_id,
        feasible=True,
        policy_allowed=True,
        risk_score=0.2,
        confidence_score=0.8,
        evidence_score=0.8,
        utility_score=0.8,
        reversibility_score=0.9,
        total_score=total_score,
    )


def test_selector_picks_highest_ranked_candidate() -> None:
    result = select_candidate(
        (
            candidate("candidate-1"),
            candidate("candidate-2"),
        ),
        (
            assessment("assessment-1", "candidate-1", 0.6),
            assessment("assessment-2", "candidate-2", 0.9),
        ),
    )

    assert result.selected is not None
    assert result.selected.candidate.candidate_id == "candidate-2"
    assert result.disposition is DecisionDisposition.SELECT_ACTION


def test_selector_returns_no_safe_action_without_acceptance() -> None:
    result = select_candidate((), ())

    assert result.selected is None
    assert (
        result.disposition
        is DecisionDisposition.NO_SAFE_ACTION
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_rationale.py" @'
from forge.autonomous_decision.models import DecisionContext
from forge.autonomous_decision.rationale import build_rationale
from forge.autonomous_decision.states import DecisionDisposition


def test_no_safe_action_rationale_is_explicit() -> None:
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a1_read",
        approval_state="pending",
        repository_fingerprint="fingerprint-1",
        policy_version="1.0",
    )

    rationale = build_rationale(
        context=context,
        disposition=DecisionDisposition.NO_SAFE_ACTION,
        selected=None,
        assessments=(),
    )

    assert "No candidate satisfied" in rationale.summary
    assert "context=context-1" in rationale.factors
'@

Write-Utf8NoBom "tests\test_autonomous_decision_replay_guard.py" @'
import pytest

from forge.autonomous_decision.errors import DecisionReplayError
from forge.autonomous_decision.models import DecisionRecord
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.states import (
    DecisionDisposition,
    DecisionKind,
)


def record(
    decision_id: str,
    rationale: str,
) -> DecisionRecord:
    return DecisionRecord(
        decision_id=decision_id,
        request_id="request-1",
        context_id="context-1",
        decision_kind=DecisionKind.STOP,
        disposition=DecisionDisposition.NO_SAFE_ACTION,
        rationale=rationale,
        confidence=0.0,
        context_fingerprint="fingerprint-1",
    )


def test_identical_replay_is_idempotent() -> None:
    guard = DecisionReplayGuard()
    first = record("decision-1", "No safe action.")

    assert guard.check_and_record(first) == first
    assert guard.check_and_record(first) == first


def test_conflicting_replay_is_rejected() -> None:
    guard = DecisionReplayGuard()
    guard.check_and_record(
        record("decision-1", "No safe action.")
    )

    with pytest.raises(DecisionReplayError):
        guard.check_and_record(
            record("decision-2", "Different decision.")
        )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_decision_journal.py" @'
import pytest

from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.errors import DecisionContractError
from forge.autonomous_decision.models import DecisionRecord
from forge.autonomous_decision.states import (
    DecisionDisposition,
    DecisionKind,
)


def record() -> DecisionRecord:
    return DecisionRecord(
        decision_id="decision-1",
        request_id="request-1",
        context_id="context-1",
        decision_kind=DecisionKind.STOP,
        disposition=DecisionDisposition.NO_SAFE_ACTION,
        rationale="No safe action.",
        confidence=0.0,
        context_fingerprint="fingerprint-1",
    )


def test_journal_is_append_only() -> None:
    journal = InMemoryDecisionJournal()
    journal.append(record())

    assert len(journal.all_records()) == 1

    with pytest.raises(DecisionContractError):
        journal.append(record())
'@

Write-Utf8NoBom "tests\test_autonomous_decision_decision_service.py" @'
from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.decision_service import (
    AutonomousDecisionService,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.states import (
    DecisionDisposition,
)


def test_decision_service_selects_supported_next_action() -> None:
    service = AutonomousDecisionService(
        policy=AutonomousDecisionPolicy(),
        journal=InMemoryDecisionJournal(),
        replay_guard=DecisionReplayGuard(),
    )
    request = DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=(
            "evidence-1",
            "evidence-2",
            "evidence-3",
        ),
        policy_version="1.0",
    )

    result = service.decide(request, context)

    assert result.record.selected_candidate_id is not None
    assert result.stop is None
    assert (
        result.record.disposition
        is DecisionDisposition.SELECT_ACTION
    )


def test_decision_service_returns_stop_without_evidence() -> None:
    service = AutonomousDecisionService(
        policy=AutonomousDecisionPolicy(),
        journal=InMemoryDecisionJournal(),
        replay_guard=DecisionReplayGuard(),
    )
    request = DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        policy_version="1.0",
    )

    result = service.decide(request, context)

    assert (
        result.record.disposition
        is DecisionDisposition.NO_SAFE_ACTION
    )
    assert result.stop is not None
'@

Write-Host ""
Write-Host "M5.4 Package 3 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_decision_selector.py `
    .\tests\test_autonomous_decision_rationale.py `
    .\tests\test_autonomous_decision_replay_guard.py `
    .\tests\test_autonomous_decision_decision_journal.py `
    .\tests\test_autonomous_decision_decision_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.4 Package 3 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.4 PACKAGE 3 COMPLETE" -ForegroundColor Green

git status --short