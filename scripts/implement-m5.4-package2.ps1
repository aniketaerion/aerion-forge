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
    throw "M5.4 Package 2 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_decision\risk_assessor.py" @'
"""Deterministic risk assessment for decision candidates."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import CandidateActionKind


@dataclass(frozen=True, slots=True)
class RiskAssessment:
    """Normalized risk score and explainable factors."""

    score: float
    factors: tuple[str, ...]


_RISK_CLASS_SCORES = {
    "low": 0.20,
    "medium": 0.50,
    "high": 0.80,
    "critical": 1.00,
}


def assess_risk(
    candidate: CandidateAction,
    context: DecisionContext,
) -> RiskAssessment:
    """Assess candidate risk using explicit bounded factors."""
    score = _RISK_CLASS_SCORES.get(
        candidate.risk_class.casefold(),
        1.0,
    )
    factors: list[str] = [
        f"risk_class={candidate.risk_class.casefold()}"
    ]

    if not candidate.reversible:
        score += 0.15
        factors.append("irreversible")

    if candidate.approval_required:
        score += 0.05
        factors.append("approval_required")

    if candidate.target_step_id in context.failed_step_ids:
        score += 0.10
        factors.append("targets_failed_step")

    if candidate.action_kind in {
        CandidateActionKind.ROLLBACK_CURRENT_STEP,
        CandidateActionKind.CANCEL_MISSION,
    }:
        score += 0.10
        factors.append("destructive_or_terminal_action")

    if context.unresolved_findings:
        score += min(
            0.15,
            len(context.unresolved_findings) * 0.03,
        )
        factors.append("unresolved_findings")

    return RiskAssessment(
        score=round(min(score, 1.0), 6),
        factors=tuple(factors),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\confidence_assessor.py" @'
"""Deterministic confidence assessment."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)


@dataclass(frozen=True, slots=True)
class ConfidenceAssessment:
    """Normalized confidence score and rationale."""

    score: float
    factors: tuple[str, ...]


def assess_confidence(
    candidate: CandidateAction,
    context: DecisionContext,
) -> ConfidenceAssessment:
    """Assess confidence from evidence and state consistency."""
    score = 0.40
    factors: list[str] = ["base_confidence"]

    evidence_count = len(
        set(candidate.evidence_references)
        | set(context.evidence_references)
    )
    if evidence_count:
        score += min(0.30, evidence_count * 0.05)
        factors.append(f"evidence_count={evidence_count}")
    else:
        score -= 0.20
        factors.append("no_evidence")

    if candidate.target_step_id is not None:
        if candidate.target_step_id == context.current_step_id:
            score += 0.15
            factors.append("matches_current_step")
        elif candidate.target_step_id in context.failed_step_ids:
            score += 0.10
            factors.append("matches_failed_step")
        else:
            score -= 0.15
            factors.append("step_context_mismatch")

    if context.unresolved_findings:
        score -= min(
            0.20,
            len(context.unresolved_findings) * 0.04,
        )
        factors.append("unresolved_findings")

    if context.approval_state == "approved":
        score += 0.05
        factors.append("approved_context")

    return ConfidenceAssessment(
        score=round(max(0.0, min(score, 1.0)), 6),
        factors=tuple(factors),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\evidence_assessor.py" @'
"""Evidence-quality assessment for autonomous decisions."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)


@dataclass(frozen=True, slots=True)
class EvidenceAssessment:
    """Normalized evidence score and explainable factors."""

    score: float
    factors: tuple[str, ...]


def assess_evidence(
    candidate: CandidateAction,
    context: DecisionContext,
) -> EvidenceAssessment:
    """Assess available evidence deterministically."""
    candidate_evidence = set(candidate.evidence_references)
    context_evidence = set(context.evidence_references)
    combined = candidate_evidence | context_evidence

    if not combined:
        return EvidenceAssessment(
            score=0.0,
            factors=("no_evidence",),
        )

    score = 0.35
    factors: list[str] = [
        f"unique_evidence={len(combined)}"
    ]

    score += min(0.35, len(combined) * 0.07)

    overlap = candidate_evidence.intersection(context_evidence)
    if overlap:
        score += min(0.15, len(overlap) * 0.05)
        factors.append(f"shared_evidence={len(overlap)}")

    if context.repository_fingerprint:
        score += 0.10
        factors.append("repository_fingerprint_present")

    if context.unresolved_findings:
        score -= min(
            0.20,
            len(context.unresolved_findings) * 0.04,
        )
        factors.append("unresolved_findings")

    return EvidenceAssessment(
        score=round(max(0.0, min(score, 1.0)), 6),
        factors=tuple(factors),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\utility_assessor.py" @'
"""Expected-utility and reversibility assessment."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import CandidateAction
from forge.autonomous_decision.states import CandidateActionKind


@dataclass(frozen=True, slots=True)
class UtilityAssessment:
    """Normalized utility and reversibility scores."""

    utility_score: float
    reversibility_score: float
    factors: tuple[str, ...]


_BASE_UTILITY = {
    CandidateActionKind.EXECUTE_NEXT_STEP: 0.85,
    CandidateActionKind.RETRY_CURRENT_STEP: 0.65,
    CandidateActionKind.ROLLBACK_CURRENT_STEP: 0.45,
    CandidateActionKind.REPLAN_REMAINING_WORK: 0.60,
    CandidateActionKind.REQUEST_APPROVAL: 0.50,
    CandidateActionKind.PAUSE_MISSION: 0.35,
    CandidateActionKind.ESCALATE_MISSION: 0.40,
    CandidateActionKind.COMPLETE_MISSION: 1.00,
    CandidateActionKind.CANCEL_MISSION: 0.10,
}


def assess_utility(
    candidate: CandidateAction,
) -> UtilityAssessment:
    """Assess expected mission utility and reversibility."""
    utility = _BASE_UTILITY[candidate.action_kind]
    factors: list[str] = [
        f"action={candidate.action_kind.value}"
    ]

    utility -= min(0.30, candidate.expected_cost * 0.05)
    if candidate.expected_cost:
        factors.append(
            f"expected_cost={candidate.expected_cost}"
        )

    if not candidate.expected_effects:
        utility -= 0.15
        factors.append("no_expected_effects")

    reversibility = 0.90 if candidate.reversible else 0.10
    factors.append(
        "reversible"
        if candidate.reversible
        else "irreversible"
    )

    return UtilityAssessment(
        utility_score=round(
            max(0.0, min(utility, 1.0)),
            6,
        ),
        reversibility_score=reversibility,
        factors=tuple(factors),
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\scoring.py" @'
"""Deterministic candidate scoring."""

from __future__ import annotations

from forge.autonomous_decision.confidence_assessor import (
    ConfidenceAssessment,
)
from forge.autonomous_decision.evidence_assessor import (
    EvidenceAssessment,
)
from forge.autonomous_decision.policies import (
    DecisionWeightPolicy,
)
from forge.autonomous_decision.risk_assessor import (
    RiskAssessment,
)
from forge.autonomous_decision.utility_assessor import (
    UtilityAssessment,
)


def calculate_total_score(
    *,
    risk: RiskAssessment,
    confidence: ConfidenceAssessment,
    evidence: EvidenceAssessment,
    utility: UtilityAssessment,
    weights: DecisionWeightPolicy,
) -> float:
    """Calculate the documented deterministic total score."""
    total = (
        weights.utility_weight * utility.utility_score
        + weights.confidence_weight * confidence.score
        + weights.evidence_weight * evidence.score
        + weights.reversibility_weight
        * utility.reversibility_score
        - weights.risk_weight * risk.score
    )

    return round(total, 6)
'@

Write-Utf8NoBom "forge\autonomous_decision\assessment_service.py" @'
"""Full explainable assessment of prepared candidates."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.candidate_service import (
    PreparedCandidate,
)
from forge.autonomous_decision.confidence_assessor import (
    assess_confidence,
)
from forge.autonomous_decision.evidence_assessor import (
    assess_evidence,
)
from forge.autonomous_decision.identifiers import (
    candidate_assessment_identifier,
)
from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.risk_assessor import assess_risk
from forge.autonomous_decision.scoring import (
    calculate_total_score,
)
from forge.autonomous_decision.states import (
    CandidateRejectionReason,
)
from forge.autonomous_decision.utility_assessor import (
    assess_utility,
)


@dataclass(frozen=True, slots=True)
class CandidateAssessmentService:
    """Assess one prepared candidate."""

    policy: AutonomousDecisionPolicy

    def assess(
        self,
        prepared: PreparedCandidate,
        context: DecisionContext,
    ) -> CandidateAssessment:
        candidate = prepared.candidate
        risk = assess_risk(candidate, context)
        confidence = assess_confidence(candidate, context)
        evidence = assess_evidence(candidate, context)
        utility = assess_utility(candidate)

        rejection_reasons = list(
            prepared.rejection_reasons
        )

        thresholds = self.policy.thresholds

        if risk.score > thresholds.maximum_risk_score:
            rejection_reasons.append(
                CandidateRejectionReason.RISK_THRESHOLD_EXCEEDED
            )

        if (
            confidence.score
            < thresholds.minimum_confidence_score
        ):
            rejection_reasons.append(
                CandidateRejectionReason.CONFIDENCE_BELOW_THRESHOLD
            )

        if evidence.score < thresholds.minimum_evidence_score:
            rejection_reasons.append(
                CandidateRejectionReason.EVIDENCE_INSUFFICIENT
            )

        if utility.utility_score < thresholds.minimum_utility_score:
            rejection_reasons.append(
                CandidateRejectionReason.POLICY_VIOLATION
            )

        if (
            not candidate.reversible
            and utility.reversibility_score
            < thresholds.minimum_reversibility_for_mutation
        ):
            rejection_reasons.append(
                CandidateRejectionReason.POLICY_VIOLATION
            )

        rejection_reasons = list(
            dict.fromkeys(rejection_reasons)
        )

        accepted = not rejection_reasons

        total_score = calculate_total_score(
            risk=risk,
            confidence=confidence,
            evidence=evidence,
            utility=utility,
            weights=self.policy.weights,
        )

        warnings = tuple(
            dict.fromkeys(
                prepared.feasibility.warnings
                + risk.factors
                + confidence.factors
                + evidence.factors
                + utility.factors
            )
        )

        payload = {
            "candidate_id": candidate.candidate_id,
            "context_id": context.context_id,
            "policy_version": context.policy_version,
            "total_score": total_score,
        }

        return CandidateAssessment(
            assessment_id=candidate_assessment_identifier(
                payload
            ),
            candidate_id=candidate.candidate_id,
            feasible=prepared.feasibility.feasible,
            policy_allowed=(
                prepared.policy.allowed and accepted
            ),
            risk_score=risk.score,
            confidence_score=confidence.score,
            evidence_score=evidence.score,
            utility_score=utility.utility_score,
            reversibility_score=utility.reversibility_score,
            total_score=total_score,
            rejection_reasons=tuple(rejection_reasons),
            warnings=warnings,
        )
'@

Write-Utf8NoBom "forge\autonomous_decision\ranking.py" @'
"""Deterministic ranking of accepted candidate assessments."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    """Candidate joined with its assessment and rank."""

    rank: int
    candidate: CandidateAction
    assessment: CandidateAssessment


def rank_candidates(
    candidates: tuple[CandidateAction, ...],
    assessments: tuple[CandidateAssessment, ...],
) -> tuple[RankedCandidate, ...]:
    """Rank accepted candidates using documented tie breakers."""
    candidate_by_id = {
        candidate.candidate_id: candidate
        for candidate in candidates
    }

    accepted = [
        assessment
        for assessment in assessments
        if (
            assessment.feasible
            and assessment.policy_allowed
            and not assessment.rejection_reasons
        )
    ]

    ordered = sorted(
        accepted,
        key=lambda assessment: (
            -assessment.total_score,
            assessment.risk_score,
            -assessment.confidence_score,
            -assessment.evidence_score,
            -assessment.reversibility_score,
            assessment.candidate_id,
        ),
    )

    return tuple(
        RankedCandidate(
            rank=index,
            candidate=candidate_by_id[
                assessment.candidate_id
            ],
            assessment=assessment,
        )
        for index, assessment in enumerate(
            ordered,
            start=1,
        )
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_risk_assessor.py" @'
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.risk_assessor import assess_risk
from forge.autonomous_decision.states import (
    CandidateActionKind,
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


def test_irreversible_high_risk_action_scores_high() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.CANCEL_MISSION,
        description="Cancel mission.",
        required_authority="a2_modify",
        risk_class="high",
        reversible=False,
        evidence_references=("evidence-1",),
        source=CandidateSource.ORCHESTRATION_STATE,
    )

    result = assess_risk(candidate, context())

    assert result.score == 1.0
    assert "irreversible" in result.factors
'@

Write-Utf8NoBom "tests\test_autonomous_decision_confidence_assessor.py" @'
from forge.autonomous_decision.confidence_assessor import (
    assess_confidence,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def test_matching_step_and_evidence_raise_confidence() -> None:
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        current_step_id="step-1",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        evidence_references=("evidence-1",),
        policy_version="1.0",
    )
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

    result = assess_confidence(candidate, context)

    assert result.score >= 0.60
    assert "matches_current_step" in result.factors
'@

Write-Utf8NoBom "tests\test_autonomous_decision_evidence_assessor.py" @'
from forge.autonomous_decision.evidence_assessor import (
    assess_evidence,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def test_no_evidence_scores_zero() -> None:
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
        authority_level="a1_read",
        approval_state="approved",
        repository_fingerprint="fingerprint-1",
        policy_version="1.0",
    )
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.PAUSE_MISSION,
        description="Pause mission.",
        required_authority="a1_read",
        risk_class="low",
        source=CandidateSource.ORCHESTRATION_STATE,
    )

    result = assess_evidence(candidate, context)

    assert result.score == 0.0
    assert result.factors == ("no_evidence",)
'@

Write-Utf8NoBom "tests\test_autonomous_decision_scoring.py" @'
from forge.autonomous_decision.confidence_assessor import (
    ConfidenceAssessment,
)
from forge.autonomous_decision.evidence_assessor import (
    EvidenceAssessment,
)
from forge.autonomous_decision.policies import (
    DecisionWeightPolicy,
)
from forge.autonomous_decision.risk_assessor import RiskAssessment
from forge.autonomous_decision.scoring import (
    calculate_total_score,
)
from forge.autonomous_decision.utility_assessor import (
    UtilityAssessment,
)


def test_total_score_matches_documented_formula() -> None:
    score = calculate_total_score(
        risk=RiskAssessment(score=0.2, factors=()),
        confidence=ConfidenceAssessment(
            score=0.8,
            factors=(),
        ),
        evidence=EvidenceAssessment(
            score=0.7,
            factors=(),
        ),
        utility=UtilityAssessment(
            utility_score=0.9,
            reversibility_score=1.0,
            factors=(),
        ),
        weights=DecisionWeightPolicy(),
    )

    assert score == 0.735
'@

Write-Utf8NoBom "tests\test_autonomous_decision_assessment_service.py" @'
from forge.autonomous_decision.assessment_service import (
    CandidateAssessmentService,
)
from forge.autonomous_decision.candidate_service import (
    PreparedCandidate,
)
from forge.autonomous_decision.feasibility import (
    FeasibilityResult,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    DecisionContext,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.policy_filter import (
    PolicyFilterResult,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateSource,
)


def test_assessment_service_accepts_supported_candidate() -> None:
    candidate = CandidateAction(
        candidate_id="candidate-1",
        action_kind=CandidateActionKind.EXECUTE_NEXT_STEP,
        target_step_id="step-1",
        description="Execute step.",
        required_authority="a2_modify",
        risk_class="medium",
        expected_effects=("Step completed.",),
        evidence_references=(
            "evidence-1",
            "evidence-2",
            "evidence-3",
        ),
        source=CandidateSource.APPROVED_PLAN,
    )
    context = DecisionContext(
        context_id="context-1",
        mission_id="mission-1",
        session_id="session-1",
        mission_state="executing",
        orchestration_state="ready",
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
    prepared = PreparedCandidate(
        candidate=candidate,
        feasibility=FeasibilityResult(
            feasible=True,
            rejection_reasons=(),
        ),
        policy=PolicyFilterResult(
            allowed=True,
            rejection_reasons=(),
        ),
    )

    result = CandidateAssessmentService(
        policy=AutonomousDecisionPolicy()
    ).assess(prepared, context)

    assert result.feasible
    assert result.policy_allowed
    assert result.rejection_reasons == ()
    assert result.total_score > 0.0
'@

Write-Utf8NoBom "tests\test_autonomous_decision_ranking.py" @'
from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
)
from forge.autonomous_decision.ranking import rank_candidates
from forge.autonomous_decision.states import (
    CandidateActionKind,
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
        utility_score=0.7,
        reversibility_score=0.9,
        total_score=total_score,
    )


def test_higher_score_ranks_first() -> None:
    candidates = (
        candidate("candidate-1"),
        candidate("candidate-2"),
    )
    assessments = (
        assessment(
            "assessment-1",
            "candidate-1",
            0.60,
        ),
        assessment(
            "assessment-2",
            "candidate-2",
            0.80,
        ),
    )

    ranked = rank_candidates(candidates, assessments)

    assert ranked[0].candidate.candidate_id == "candidate-2"
    assert ranked[0].rank == 1
'@

Write-Host ""
Write-Host "M5.4 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_decision_risk_assessor.py `
    .\tests\test_autonomous_decision_confidence_assessor.py `
    .\tests\test_autonomous_decision_evidence_assessor.py `
    .\tests\test_autonomous_decision_scoring.py `
    .\tests\test_autonomous_decision_assessment_service.py `
    .\tests\test_autonomous_decision_ranking.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.4 Package 2 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.4 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short