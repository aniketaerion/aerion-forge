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
    throw "M5.4 Package 1 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_decision\candidate_generator.py" @'
"""Bounded deterministic candidate generation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.identifiers import (
    candidate_action_identifier,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


@dataclass(frozen=True, slots=True)
class CandidateGenerationResult:
    """Generated candidates and truncation metadata."""

    candidates: tuple[CandidateAction, ...]
    truncated: bool


def _candidate(
    *,
    context: DecisionContext,
    action_kind: CandidateActionKind,
    description: str,
    source: CandidateSource,
    target_step_id: str | None = None,
    approval_required: bool = False,
    risk_class: str = "medium",
    reversible: bool = True,
    dependencies: tuple[str, ...] = (),
    evidence_references: tuple[str, ...] = (),
) -> CandidateAction:
    payload = {
        "context_id": context.context_id,
        "action_kind": action_kind.value,
        "target_step_id": target_step_id,
        "description": description,
        "source": source.value,
    }

    return CandidateAction(
        candidate_id=candidate_action_identifier(payload),
        action_kind=action_kind,
        target_step_id=target_step_id,
        description=description,
        required_authority=context.authority_level,
        approval_required=approval_required,
        risk_class=risk_class,
        expected_effects=(description,),
        reversible=reversible,
        dependencies=dependencies,
        evidence_references=evidence_references,
        source=source,
    )


def generate_candidates(
    request: DecisionRequest,
    context: DecisionContext,
    policy: AutonomousDecisionPolicy,
) -> CandidateGenerationResult:
    """Generate a deterministic finite candidate set."""
    limit = min(
        request.maximum_candidates,
        policy.thresholds.maximum_candidates,
    )
    candidates: list[CandidateAction] = []

    if context.current_step_id is not None:
        if context.current_step_id in context.failed_step_ids:
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.RETRY_CURRENT_STEP
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        f"Retry failed step {context.current_step_id}."
                    ),
                    source=CandidateSource.EXECUTION_OUTCOME,
                    evidence_references=context.evidence_references,
                )
            )
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.ROLLBACK_CURRENT_STEP
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        f"Rollback failed step "
                        f"{context.current_step_id}."
                    ),
                    source=CandidateSource.RECOVERY_POLICY,
                    approval_required=True,
                    risk_class="high",
                    evidence_references=context.evidence_references,
                )
            )
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.REPLAN_REMAINING_WORK
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        "Replan remaining work after failed step."
                    ),
                    source=CandidateSource.RECOVERY_POLICY,
                    approval_required=True,
                    risk_class="medium",
                    evidence_references=context.evidence_references,
                )
            )
        elif context.current_step_id not in context.completed_step_ids:
            candidates.append(
                _candidate(
                    context=context,
                    action_kind=(
                        CandidateActionKind.EXECUTE_NEXT_STEP
                    ),
                    target_step_id=context.current_step_id,
                    description=(
                        f"Execute current approved step "
                        f"{context.current_step_id}."
                    ),
                    source=CandidateSource.APPROVED_PLAN,
                    evidence_references=context.evidence_references,
                )
            )

    if context.approval_state != "approved":
        candidates.append(
            _candidate(
                context=context,
                action_kind=CandidateActionKind.REQUEST_APPROVAL,
                description="Request approval before continuing.",
                source=CandidateSource.ORCHESTRATION_STATE,
                approval_required=True,
                risk_class="low",
                evidence_references=context.evidence_references,
            )
        )

    if context.unresolved_findings:
        candidates.append(
            _candidate(
                context=context,
                action_kind=CandidateActionKind.PAUSE_MISSION,
                description=(
                    "Pause mission until unresolved findings are "
                    "addressed."
                ),
                source=CandidateSource.VALIDATION_FINDING,
                risk_class="low",
                evidence_references=context.evidence_references,
            )
        )

    if (
        context.current_step_id is None
        and not context.failed_step_ids
        and not context.unresolved_findings
    ):
        candidates.append(
            _candidate(
                context=context,
                action_kind=CandidateActionKind.COMPLETE_MISSION,
                description="Complete the mission.",
                source=CandidateSource.ORCHESTRATION_STATE,
                risk_class="low",
                evidence_references=context.evidence_references,
            )
        )

    candidates.append(
        _candidate(
            context=context,
            action_kind=CandidateActionKind.ESCALATE_MISSION,
            description="Escalate the mission for human review.",
            source=CandidateSource.ORCHESTRATION_STATE,
            risk_class="low",
            evidence_references=context.evidence_references,
        )
    )

    ordered = tuple(
        sorted(
            candidates,
            key=lambda candidate: (
                candidate.action_kind.value,
                candidate.target_step_id or "",
                candidate.candidate_id,
            ),
        )
    )
    truncated = len(ordered) > limit

    return CandidateGenerationResult(
        candidates=ordered[:limit],
        truncated=truncated,
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\deduplication.py" @'
"""Semantic candidate deduplication."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import CandidateAction
from forge.autonomous_decision.states import CandidateRejectionReason


@dataclass(frozen=True, slots=True)
class CandidateDeduplicationResult:
    """Unique candidates and rejected duplicate identifiers."""

    candidates: tuple[CandidateAction, ...]
    rejected: tuple[
        tuple[str, CandidateRejectionReason],
        ...,
    ]


def candidate_semantic_key(
    candidate: CandidateAction,
) -> tuple[str, str, str]:
    """Return a stable semantic candidate key."""
    return (
        candidate.action_kind.value,
        candidate.target_step_id or "",
        candidate.description.strip().casefold(),
    )


def deduplicate_candidates(
    candidates: tuple[CandidateAction, ...],
) -> CandidateDeduplicationResult:
    """Remove semantic duplicates deterministically."""
    seen: set[tuple[str, str, str]] = set()
    accepted: list[CandidateAction] = []
    rejected: list[
        tuple[str, CandidateRejectionReason]
    ] = []

    for candidate in sorted(
        candidates,
        key=lambda item: item.candidate_id,
    ):
        key = candidate_semantic_key(candidate)

        if key in seen:
            rejected.append(
                (
                    candidate.candidate_id,
                    CandidateRejectionReason.DUPLICATE,
                )
            )
            continue

        seen.add(key)
        accepted.append(candidate)

    return CandidateDeduplicationResult(
        candidates=tuple(accepted),
        rejected=tuple(rejected),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\feasibility.py" @'
"""Candidate feasibility evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
)


@dataclass(frozen=True, slots=True)
class FeasibilityResult:
    """Feasibility result for one candidate."""

    feasible: bool
    rejection_reasons: tuple[CandidateRejectionReason, ...]
    warnings: tuple[str, ...] = ()


def evaluate_feasibility(
    candidate: CandidateAction,
    context: DecisionContext,
) -> FeasibilityResult:
    """Evaluate structural feasibility without scoring."""
    reasons: list[CandidateRejectionReason] = []
    warnings: list[str] = []

    if any(
        not dependency.strip()
        for dependency in candidate.dependencies
    ):
        reasons.append(
            CandidateRejectionReason.MISSING_DEPENDENCY
        )

    if (
        candidate.target_step_id is not None
        and candidate.target_step_id
        in context.completed_step_ids
    ):
        reasons.append(
            CandidateRejectionReason.COMPLETED_STEP_REPLAY
        )

    if (
        candidate.action_kind
        is CandidateActionKind.RETRY_CURRENT_STEP
        and candidate.target_step_id
        not in context.failed_step_ids
    ):
        reasons.append(CandidateRejectionReason.INFEASIBLE)

    if (
        candidate.action_kind
        is CandidateActionKind.ROLLBACK_CURRENT_STEP
        and candidate.target_step_id is None
    ):
        reasons.append(CandidateRejectionReason.INFEASIBLE)

    if (
        candidate.action_kind
        is CandidateActionKind.COMPLETE_MISSION
        and (
            context.current_step_id is not None
            or context.failed_step_ids
            or context.unresolved_findings
        )
    ):
        reasons.append(CandidateRejectionReason.INFEASIBLE)

    if not candidate.evidence_references:
        warnings.append("Candidate has no supporting evidence.")

    return FeasibilityResult(
        feasible=not reasons,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
        warnings=tuple(warnings),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\policy_filter.py" @'
"""Hard policy filtering for decision candidates."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.states import (
    CandidateRejectionReason,
)


@dataclass(frozen=True, slots=True)
class PolicyFilterResult:
    """Policy result for one candidate."""

    allowed: bool
    rejection_reasons: tuple[CandidateRejectionReason, ...]


_RISK_RANK = {
    "low": 0.20,
    "medium": 0.50,
    "high": 0.80,
    "critical": 1.00,
}


def evaluate_candidate_policy(
    candidate: CandidateAction,
    context: DecisionContext,
    policy: AutonomousDecisionPolicy,
) -> PolicyFilterResult:
    """Apply hard policy constraints before scoring."""
    reasons: list[CandidateRejectionReason] = []

    if (
        policy.safety.require_authority_match
        and candidate.required_authority
        != context.authority_level
    ):
        reasons.append(
            CandidateRejectionReason.INSUFFICIENT_AUTHORITY
        )

    if (
        policy.safety.preserve_approval_requirements
        and candidate.approval_required
        and context.approval_state != "approved"
    ):
        reasons.append(
            CandidateRejectionReason.APPROVAL_REQUIRED
        )

    risk_score = _RISK_RANK.get(candidate.risk_class.casefold())

    if risk_score is None:
        reasons.append(
            CandidateRejectionReason.POLICY_VIOLATION
        )
    elif risk_score > policy.thresholds.maximum_risk_score:
        reasons.append(
            CandidateRejectionReason.RISK_THRESHOLD_EXCEEDED
        )

    if (
        policy.safety.require_evidence
        and not candidate.evidence_references
    ):
        reasons.append(
            CandidateRejectionReason.EVIDENCE_INSUFFICIENT
        )

    return PolicyFilterResult(
        allowed=not reasons,
        rejection_reasons=tuple(dict.fromkeys(reasons)),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\candidate_service.py" @'
"""Application service for bounded candidate preparation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.candidate_generator import (
    CandidateGenerationResult,
    generate_candidates,
)
from forge.autonomous_decision.deduplication import (
    CandidateDeduplicationResult,
    deduplicate_candidates,
)
from forge.autonomous_decision.feasibility import (
    FeasibilityResult,
    evaluate_feasibility,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.policy_filter import (
    PolicyFilterResult,
    evaluate_candidate_policy,
)
from forge.autonomous_decision.states import (
    CandidateRejectionReason,
)


@dataclass(frozen=True, slots=True)
class PreparedCandidate:
    """Candidate with hard-filter results."""

    candidate: CandidateAction
    feasibility: FeasibilityResult
    policy: PolicyFilterResult

    @property
    def accepted(self) -> bool:
        return self.feasibility.feasible and self.policy.allowed

    @property
    def rejection_reasons(
        self,
    ) -> tuple[CandidateRejectionReason, ...]:
        return tuple(
            dict.fromkeys(
                self.feasibility.rejection_reasons
                + self.policy.rejection_reasons
            )
        )


@dataclass(frozen=True, slots=True)
class CandidatePreparationResult:
    """Complete candidate-preparation result."""

    generated: CandidateGenerationResult
    deduplicated: CandidateDeduplicationResult
    prepared: tuple[PreparedCandidate, ...]

    @property
    def accepted(self) -> tuple[PreparedCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.prepared
            if candidate.accepted
        )

    @property
    def rejected(self) -> tuple[PreparedCandidate, ...]:
        return tuple(
            candidate
            for candidate in self.prepared
            if not candidate.accepted
        )


@dataclass(frozen=True, slots=True)
class CandidatePreparationService:
    """Generate, deduplicate, and hard-filter candidates."""

    policy: AutonomousDecisionPolicy

    def prepare(
        self,
        request: DecisionRequest,
        context: DecisionContext,
    ) -> CandidatePreparationResult:
        generated = generate_candidates(
            request,
            context,
            self.policy,
        )
        deduplicated = deduplicate_candidates(
            generated.candidates
        )

        prepared = tuple(
            PreparedCandidate(
                candidate=candidate,
                feasibility=evaluate_feasibility(
                    candidate,
                    context,
                ),
                policy=evaluate_candidate_policy(
                    candidate,
                    context,
                    self.policy,
                ),
            )
            for candidate in deduplicated.candidates
        )

        return CandidatePreparationResult(
            generated=generated,
            deduplicated=deduplicated,
            prepared=prepared,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_candidate_generator.py" @'
from forge.autonomous_decision.candidate_generator import (
    generate_candidates,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
)


def request() -> DecisionRequest:
    return DecisionRequest(
        request_id="request-1",
        mission_id="mission-1",
        session_id="session-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        requested_by="Aerion",
    )


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_generator_produces_bounded_candidates() -> None:
    result = generate_candidates(
        request(),
        context(),
        AutonomousDecisionPolicy(),
    )

    assert len(result.candidates) <= 20
    assert any(
        candidate.action_kind
        is CandidateActionKind.EXECUTE_NEXT_STEP
        for candidate in result.candidates
    )


def test_failed_step_generates_recovery_candidates() -> None:
    failed_context = context().model_copy(
        update={"failed_step_ids": ("step-1",)}
    )

    result = generate_candidates(
        request(),
        failed_context,
        AutonomousDecisionPolicy(),
    )

    kinds = {
        candidate.action_kind
        for candidate in result.candidates
    }

    assert CandidateActionKind.RETRY_CURRENT_STEP in kinds
    assert CandidateActionKind.ROLLBACK_CURRENT_STEP in kinds
    assert CandidateActionKind.REPLAN_REMAINING_WORK in kinds
'@

Write-Utf8NoBom "tests\test_autonomous_decision_deduplication.py" @'
from forge.autonomous_decision.deduplication import (
    deduplicate_candidates,
)
from forge.autonomous_decision.models import CandidateAction
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
)


def candidate(candidate_id: str) -> CandidateAction:
    return CandidateAction(
        candidate_id=candidate_id,
        action_kind=CandidateActionKind.PAUSE_MISSION,
        description="Pause mission.",
        required_authority="a1_read",
        risk_class="low",
        evidence_references=("evidence-1",),
        source=CandidateSource.ORCHESTRATION_STATE,
    )


def test_semantic_duplicates_are_rejected() -> None:
    result = deduplicate_candidates(
        (candidate("candidate-2"), candidate("candidate-1"))
    )

    assert len(result.candidates) == 1
    assert result.rejected == (
        (
            "candidate-2",
            CandidateRejectionReason.DUPLICATE,
        ),
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_feasibility.py" @'
from forge.autonomous_decision.feasibility import (
    evaluate_feasibility,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
)


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        completed_step_ids=("step-1",),
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_completed_step_replay_is_infeasible() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.EXECUTE_NEXT_STEP,
        target_step_id="step-1",
        description="Execute step.",
        required_authority="a2_modify",
        risk_class="medium",
        evidence_references=("evidence-1",),
        source=CandidateSource.APPROVED_PLAN,
    )

    result = evaluate_feasibility(candidate, context())

    assert not result.feasible
    assert (
        CandidateRejectionReason.COMPLETED_STEP_REPLAY
        in result.rejection_reasons
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_policy_filter.py" @'
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.policy_filter import (
    evaluate_candidate_policy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
)


def context() -> DecisionContext:
    return DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )


def test_high_risk_candidate_is_rejected() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.ROLLBACK_CURRENT_STEP,
        target_step_id="step-1",
        description="Rollback step.",
        required_authority="a2_modify",
        approval_required=False,
        risk_class="high",
        evidence_references=("evidence-1",),
        source=CandidateSource.RECOVERY_POLICY,
    )

    result = evaluate_candidate_policy(
        candidate,
        context(),
        AutonomousDecisionPolicy(),
    )

    assert not result.allowed
    assert (
        CandidateRejectionReason.RISK_THRESHOLD_EXCEEDED
        in result.rejection_reasons
    )


def test_candidate_without_evidence_is_rejected() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.PAUSE_MISSION,
        description="Pause mission.",
        required_authority="a2_modify",
        risk_class="low",
        source=CandidateSource.ORCHESTRATION_STATE,
    )

    result = evaluate_candidate_policy(
        candidate,
        context(),
        AutonomousDecisionPolicy(),
    )

    assert (
        CandidateRejectionReason.EVIDENCE_INSUFFICIENT
        in result.rejection_reasons
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_candidate_service.py" @'
from forge.autonomous_decision.candidate_service import (
    CandidatePreparationService,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)


def test_candidate_service_prepares_candidates() -> None:
    service = CandidatePreparationService(
        policy=AutonomousDecisionPolicy()
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
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )

    result = service.prepare(request, context)

    assert result.prepared
    assert result.accepted
    assert all(
        item.rejection_reasons == ()
        for item in result.accepted
    )
'@

Write-Host ""
Write-Host "M5.4 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_decision_candidate_generator.py `
    .\tests\test_autonomous_decision_deduplication.py `
    .\tests\test_autonomous_decision_feasibility.py `
    .\tests\test_autonomous_decision_policy_filter.py `
    .\tests\test_autonomous_decision_candidate_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.4 Package 1 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.4 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short