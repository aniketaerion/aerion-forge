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
    throw "M5.4 Package 0 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_decision\errors.py" @'
"""Typed errors for the autonomous decision engine."""

from __future__ import annotations


class AutonomousDecisionError(RuntimeError):
    """Base error for autonomous decision failures."""


class DecisionContractError(AutonomousDecisionError):
    """Raised when a decision contract is invalid."""


class DecisionIdentifierError(AutonomousDecisionError):
    """Raised when a deterministic identifier cannot be created."""


class DecisionPolicyError(AutonomousDecisionError):
    """Raised when decision policy is unsafe or inconsistent."""


class CandidateRejectedError(AutonomousDecisionError):
    """Raised when a candidate violates a hard decision constraint."""


class DecisionReplayError(AutonomousDecisionError):
    """Raised when a conflicting decision replay is detected."""
'@

Write-Utf8NoBom "forge\autonomous_decision\states.py" @'
"""Enumerations for the autonomous decision engine."""

from __future__ import annotations

from enum import StrEnum


class DecisionKind(StrEnum):
    """Decision categories supported by M5.4."""

    NEXT_ACTION = "next_action"
    RECOVERY = "recovery"
    COMPLETION = "completion"
    APPROVAL = "approval"
    STOP = "stop"


class DecisionDisposition(StrEnum):
    """Committed decision dispositions."""

    SELECT_ACTION = "select_action"
    RETRY = "retry"
    ROLLBACK = "rollback"
    REPLAN = "replan"
    PAUSE = "pause"
    ESCALATE = "escalate"
    COMPLETE = "complete"
    CANCEL = "cancel"
    NO_SAFE_ACTION = "no_safe_action"


class CandidateActionKind(StrEnum):
    """Candidate engineering action kinds."""

    EXECUTE_NEXT_STEP = "execute_next_step"
    RETRY_CURRENT_STEP = "retry_current_step"
    ROLLBACK_CURRENT_STEP = "rollback_current_step"
    REPLAN_REMAINING_WORK = "replan_remaining_work"
    REQUEST_APPROVAL = "request_approval"
    PAUSE_MISSION = "pause_mission"
    ESCALATE_MISSION = "escalate_mission"
    COMPLETE_MISSION = "complete_mission"
    CANCEL_MISSION = "cancel_mission"


class CandidateSource(StrEnum):
    """Provenance of a generated candidate."""

    APPROVED_PLAN = "approved_plan"
    ORCHESTRATION_STATE = "orchestration_state"
    EXECUTION_OUTCOME = "execution_outcome"
    VALIDATION_FINDING = "validation_finding"
    RECOVERY_POLICY = "recovery_policy"
    REPOSITORY_EVIDENCE = "repository_evidence"
    HUMAN_INSTRUCTION = "human_instruction"


class CandidateRejectionReason(StrEnum):
    """Canonical hard-rejection reasons."""

    DUPLICATE = "duplicate"
    INFEASIBLE = "infeasible"
    MISSING_DEPENDENCY = "missing_dependency"
    INSUFFICIENT_AUTHORITY = "insufficient_authority"
    APPROVAL_REQUIRED = "approval_required"
    SCOPE_VIOLATION = "scope_violation"
    RISK_THRESHOLD_EXCEEDED = "risk_threshold_exceeded"
    CONFIDENCE_BELOW_THRESHOLD = "confidence_below_threshold"
    EVIDENCE_INSUFFICIENT = "evidence_insufficient"
    COMPLETED_STEP_REPLAY = "completed_step_replay"
    BUDGET_EXHAUSTED = "budget_exhausted"
    POLICY_VIOLATION = "policy_violation"


class DecisionStopKind(StrEnum):
    """Explicit stop outcomes."""

    APPROVAL_REQUIRED = "approval_required"
    CLARIFICATION_REQUIRED = "clarification_required"
    EVIDENCE_REQUIRED = "evidence_required"
    POLICY_BLOCKED = "policy_blocked"
    RISK_TOO_HIGH = "risk_too_high"
    NO_SAFE_ACTION = "no_safe_action"
    MISSION_COMPLETE = "mission_complete"
    CANCELLED = "cancelled"
'@

Write-Utf8NoBom "forge\autonomous_decision\identifiers.py" @'
"""Stable deterministic identifiers for decision records."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from forge.autonomous_decision.errors import DecisionIdentifierError


def _normalize(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {
            str(key): _normalize(item)
            for key, item in sorted(
                value.items(),
                key=lambda pair: str(pair[0]),
            )
        }

    if isinstance(value, (list, tuple, set, frozenset)):
        normalized = [_normalize(item) for item in value]
        if isinstance(value, (set, frozenset)):
            normalized = sorted(
                normalized,
                key=lambda item: json.dumps(
                    item,
                    sort_keys=True,
                    separators=(",", ":"),
                ),
            )
        return normalized

    return value


def deterministic_decision_identifier(
    prefix: str,
    payload: Mapping[str, Any],
) -> str:
    """Return a stable identifier from canonical JSON."""
    if not prefix.strip():
        raise DecisionIdentifierError(
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
        raise DecisionIdentifierError(
            f"Unable to serialize identifier payload for {prefix}."
        ) from exc

    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:24]
    return f"{prefix}-{digest}"


def decision_request_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-request",
        payload,
    )


def decision_context_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-context",
        payload,
    )


def candidate_action_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "candidate-action",
        payload,
    )


def candidate_assessment_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "candidate-assessment",
        payload,
    )


def decision_record_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-record",
        payload,
    )


def decision_stop_identifier(
    payload: Mapping[str, Any],
) -> str:
    return deterministic_decision_identifier(
        "decision-stop",
        payload,
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\policies.py" @'
"""Default-safe policies for autonomous engineering decisions."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_decision.errors import DecisionPolicyError


class DecisionThresholdPolicy(BaseModel):
    """Normalized score thresholds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maximum_candidates: int = Field(default=20, ge=1, le=200)
    maximum_risk_score: float = Field(default=0.60, ge=0.0, le=1.0)
    minimum_confidence_score: float = Field(
        default=0.55,
        ge=0.0,
        le=1.0,
    )
    minimum_evidence_score: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
    )
    minimum_utility_score: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )
    minimum_reversibility_for_mutation: float = Field(
        default=0.50,
        ge=0.0,
        le=1.0,
    )


class DecisionWeightPolicy(BaseModel):
    """Explicit deterministic scoring weights."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    utility_weight: float = Field(default=0.35, ge=0.0, le=1.0)
    confidence_weight: float = Field(default=0.25, ge=0.0, le=1.0)
    evidence_weight: float = Field(default=0.20, ge=0.0, le=1.0)
    reversibility_weight: float = Field(default=0.10, ge=0.0, le=1.0)
    risk_weight: float = Field(default=0.10, ge=0.0, le=1.0)

    @model_validator(mode="after")
    def validate_total_weight(
        self,
    ) -> DecisionWeightPolicy:
        total = (
            self.utility_weight
            + self.confidence_weight
            + self.evidence_weight
            + self.reversibility_weight
            + self.risk_weight
        )

        if abs(total - 1.0) > 1e-9:
            raise DecisionPolicyError(
                "Decision scoring weights must total exactly 1.0."
            )

        return self


class DecisionSafetyPolicy(BaseModel):
    """Hard safety requirements for decision selection."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    dry_run_by_default: bool = True
    require_evidence: bool = True
    require_scope_match: bool = True
    require_authority_match: bool = True
    preserve_approval_requirements: bool = True
    reject_completed_step_replay: bool = True
    reject_duplicate_candidates: bool = True
    reject_conflicting_replay: bool = True
    allow_tool_execution: bool = False
    allow_repository_mutation: bool = False
    allow_hidden_assumptions: bool = False

    @model_validator(mode="after")
    def validate_safety(
        self,
    ) -> DecisionSafetyPolicy:
        violations: list[str] = []

        if not self.require_evidence:
            violations.append("evidence is mandatory")
        if not self.require_scope_match:
            violations.append("scope matching is mandatory")
        if not self.require_authority_match:
            violations.append("authority matching is mandatory")
        if not self.preserve_approval_requirements:
            violations.append(
                "approval requirements must be preserved"
            )
        if not self.reject_completed_step_replay:
            violations.append(
                "completed-step replay must be rejected"
            )
        if not self.reject_duplicate_candidates:
            violations.append(
                "duplicate candidates must be rejected"
            )
        if not self.reject_conflicting_replay:
            violations.append(
                "conflicting decision replay must be rejected"
            )
        if self.allow_tool_execution:
            violations.append(
                "M5.4 cannot execute tools"
            )
        if self.allow_repository_mutation:
            violations.append(
                "M5.4 cannot mutate repository content"
            )
        if self.allow_hidden_assumptions:
            violations.append(
                "hidden assumptions are prohibited"
            )

        if violations:
            raise DecisionPolicyError("; ".join(violations))

        return self


class AutonomousDecisionPolicy(BaseModel):
    """Top-level M5.4 decision policy."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: str = "1.0"
    policy_version: str = "1.0"
    thresholds: DecisionThresholdPolicy = Field(
        default_factory=DecisionThresholdPolicy
    )
    weights: DecisionWeightPolicy = Field(
        default_factory=DecisionWeightPolicy
    )
    safety: DecisionSafetyPolicy = Field(
        default_factory=DecisionSafetyPolicy
    )
'@

Write-Utf8NoBom "forge\autonomous_decision\models.py" @'
"""Immutable contracts for the autonomous decision engine."""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
    DecisionDisposition,
    DecisionKind,
    DecisionStopKind,
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class FrozenDecisionContract(BaseModel):
    """Base immutable decision contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class DecisionRequest(FrozenDecisionContract):
    """Request for one bounded autonomous engineering decision."""

    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    repository_root: str = Field(min_length=1)
    decision_kind: DecisionKind = DecisionKind.NEXT_ACTION
    maximum_candidates: int = Field(default=20, ge=1, le=200)
    dry_run: bool = True
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class DecisionContext(FrozenDecisionContract):
    """Evidence-bearing decision context."""

    context_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    mission_state: str = Field(min_length=1)
    orchestration_state: str = Field(min_length=1)
    current_step_id: str | None = None
    completed_step_ids: tuple[str, ...] = ()
    failed_step_ids: tuple[str, ...] = ()
    retry_count: int = Field(default=0, ge=0)
    rollback_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    authority_level: str = Field(min_length=1)
    approval_state: str = Field(min_length=1)
    repository_fingerprint: str = Field(min_length=1)
    evidence_references: tuple[str, ...] = ()
    unresolved_findings: tuple[str, ...] = ()
    policy_version: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_context_collections(
        self,
    ) -> DecisionContext:
        if len(set(self.completed_step_ids)) != len(
            self.completed_step_ids
        ):
            raise ValueError(
                "completed_step_ids cannot contain duplicates."
            )

        if len(set(self.failed_step_ids)) != len(
            self.failed_step_ids
        ):
            raise ValueError(
                "failed_step_ids cannot contain duplicates."
            )

        if set(self.completed_step_ids).intersection(
            self.failed_step_ids
        ):
            raise ValueError(
                "A step cannot be both completed and failed."
            )

        return self


class CandidateAction(FrozenDecisionContract):
    """One candidate engineering action."""

    candidate_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    action_kind: CandidateActionKind
    target_step_id: str | None = None
    description: str = Field(min_length=1)
    required_authority: str = Field(min_length=1)
    approval_required: bool = False
    risk_class: str = Field(min_length=1)
    expected_effects: tuple[str, ...] = ()
    expected_cost: float = Field(default=0.0, ge=0.0)
    reversible: bool = True
    dependencies: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    source: CandidateSource
    created_at: datetime = Field(default_factory=utc_now)


class CandidateAssessment(FrozenDecisionContract):
    """Explainable assessment of one candidate."""

    assessment_id: str = Field(min_length=1)
    candidate_id: str = Field(min_length=1)
    feasible: bool
    policy_allowed: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    confidence_score: float = Field(ge=0.0, le=1.0)
    evidence_score: float = Field(ge=0.0, le=1.0)
    utility_score: float = Field(ge=0.0, le=1.0)
    reversibility_score: float = Field(ge=0.0, le=1.0)
    total_score: float
    rejection_reasons: tuple[CandidateRejectionReason, ...] = ()
    warnings: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_assessment_disposition(
        self,
    ) -> CandidateAssessment:
        accepted = self.feasible and self.policy_allowed

        if accepted and self.rejection_reasons:
            raise ValueError(
                "Accepted candidate cannot have rejection reasons."
            )

        if not accepted and not self.rejection_reasons:
            raise ValueError(
                "Rejected candidate requires at least one reason."
            )

        return self


class DecisionRecord(FrozenDecisionContract):
    """Immutable committed autonomous decision."""

    decision_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    request_id: str = Field(min_length=1)
    context_id: str = Field(min_length=1)
    selected_candidate_id: str | None = None
    decision_kind: DecisionKind
    disposition: DecisionDisposition
    rationale: str = Field(min_length=1)
    alternative_candidate_ids: tuple[str, ...] = ()
    rejected_candidate_ids: tuple[str, ...] = ()
    assessment_ids: tuple[str, ...] = ()
    evidence_references: tuple[str, ...] = ()
    approval_required: bool = False
    confidence: float = Field(ge=0.0, le=1.0)
    context_fingerprint: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_selected_candidate(
        self,
    ) -> DecisionRecord:
        action_selected = (
            self.disposition is DecisionDisposition.SELECT_ACTION
        )

        if action_selected and self.selected_candidate_id is None:
            raise ValueError(
                "select_action decision requires selected_candidate_id."
            )

        if (
            self.disposition
            is DecisionDisposition.NO_SAFE_ACTION
            and self.selected_candidate_id is not None
        ):
            raise ValueError(
                "no_safe_action cannot select a candidate."
            )

        if (
            self.selected_candidate_id is not None
            and self.selected_candidate_id
            in self.rejected_candidate_ids
        ):
            raise ValueError(
                "Rejected candidate cannot be selected."
            )

        return self


class DecisionStop(FrozenDecisionContract):
    """Explicit stop produced when no action is selected."""

    stop_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    stop_kind: DecisionStopKind
    reason: str = Field(min_length=1)
    resumable: bool = False
    approval_required: bool = False
    evidence_references: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)
'@

Write-Utf8NoBom "forge\autonomous_decision\__init__.py" @'
"""Aerion Forge autonomous decision engine contracts."""

from forge.autonomous_decision.errors import (
    AutonomousDecisionError,
    CandidateRejectedError,
    DecisionContractError,
    DecisionIdentifierError,
    DecisionPolicyError,
    DecisionReplayError,
)
from forge.autonomous_decision.identifiers import (
    candidate_action_identifier,
    candidate_assessment_identifier,
    decision_context_identifier,
    decision_record_identifier,
    decision_request_identifier,
    decision_stop_identifier,
    deterministic_decision_identifier,
)
from forge.autonomous_decision.models import (
    CandidateAction,
    CandidateAssessment,
    DecisionContext,
    DecisionRecord,
    DecisionRequest,
    DecisionStop,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
    DecisionSafetyPolicy,
    DecisionThresholdPolicy,
    DecisionWeightPolicy,
)
from forge.autonomous_decision.states import (
    CandidateActionKind,
    CandidateRejectionReason,
    CandidateSource,
    DecisionDisposition,
    DecisionKind,
    DecisionStopKind,
)

__all__ = [
    "AutonomousDecisionError",
    "AutonomousDecisionPolicy",
    "CandidateAction",
    "CandidateActionKind",
    "CandidateAssessment",
    "CandidateRejectedError",
    "CandidateRejectionReason",
    "CandidateSource",
    "DecisionContext",
    "DecisionContractError",
    "DecisionDisposition",
    "DecisionIdentifierError",
    "DecisionKind",
    "DecisionPolicyError",
    "DecisionRecord",
    "DecisionReplayError",
    "DecisionRequest",
    "DecisionSafetyPolicy",
    "DecisionStop",
    "DecisionStopKind",
    "DecisionThresholdPolicy",
    "DecisionWeightPolicy",
    "candidate_action_identifier",
    "candidate_assessment_identifier",
    "decision_context_identifier",
    "decision_record_identifier",
    "decision_request_identifier",
    "decision_stop_identifier",
    "deterministic_decision_identifier",
]
'@

Write-Utf8NoBom "tests\test_autonomous_decision_identifiers.py" @'
from forge.autonomous_decision.identifiers import (
    candidate_action_identifier,
    decision_request_identifier,
)


def test_decision_request_identifier_is_stable() -> None:
    first = decision_request_identifier(
        {
            "mission_id": "mission-1",
            "session_id": "session-1",
        }
    )
    second = decision_request_identifier(
        {
            "session_id": "session-1",
            "mission_id": "mission-1",
        }
    )

    assert first == second
    assert first.startswith("decision-request-")


def test_candidate_identifier_has_prefix() -> None:
    result = candidate_action_identifier(
        {
            "action_kind": "execute_next_step",
            "target_step_id": "step-1",
        }
    )

    assert result.startswith("candidate-action-")
'@

Write-Utf8NoBom "tests\test_autonomous_decision_states.py" @'
from forge.autonomous_decision.states import (
    CandidateActionKind,
    DecisionDisposition,
    DecisionKind,
)


def test_decision_enumerations_are_stable() -> None:
    assert DecisionKind.NEXT_ACTION.value == "next_action"
    assert (
        DecisionDisposition.NO_SAFE_ACTION.value
        == "no_safe_action"
    )
    assert (
        CandidateActionKind.EXECUTE_NEXT_STEP.value
        == "execute_next_step"
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_policies.py" @'
import pytest

from forge.autonomous_decision.errors import DecisionPolicyError
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
    DecisionSafetyPolicy,
    DecisionWeightPolicy,
)


def test_default_policy_is_safe_and_bounded() -> None:
    policy = AutonomousDecisionPolicy()

    assert policy.safety.dry_run_by_default
    assert not policy.safety.allow_tool_execution
    assert policy.thresholds.maximum_candidates == 20


def test_weight_total_must_equal_one() -> None:
    with pytest.raises(DecisionPolicyError):
        DecisionWeightPolicy(
            utility_weight=0.50,
            confidence_weight=0.50,
            evidence_weight=0.50,
            reversibility_weight=0.10,
            risk_weight=0.10,
        )


def test_tool_execution_cannot_be_enabled() -> None:
    with pytest.raises(DecisionPolicyError):
        DecisionSafetyPolicy(
            allow_tool_execution=True,
        )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_models.py" @'
import pytest
from pydantic import ValidationError

from forge.autonomous_decision.models import (
    CandidateAssessment,
    DecisionContext,
    DecisionRecord,
)
from forge.autonomous_decision.states import (
    CandidateRejectionReason,
    DecisionDisposition,
    DecisionKind,
)


def test_context_rejects_overlapping_step_states() -> None:
    with pytest.raises(ValidationError):
        DecisionContext(
            context_id="context-1",
            mission_id="mission-1",
            session_id="session-1",
            mission_state="executing",
            orchestration_state="ready",
            completed_step_ids=("step-1",),
            failed_step_ids=("step-1",),
            authority_level="a2_modify",
            approval_state="approved",
            repository_fingerprint="fingerprint-1",
            policy_version="1.0",
        )


def test_rejected_assessment_requires_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateAssessment(
            assessment_id="assessment-1",
            candidate_id="candidate-1",
            feasible=False,
            policy_allowed=False,
            risk_score=0.5,
            confidence_score=0.5,
            evidence_score=0.5,
            utility_score=0.5,
            reversibility_score=0.5,
            total_score=0.0,
        )


def test_accepted_assessment_cannot_have_rejection_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateAssessment(
            assessment_id="assessment-1",
            candidate_id="candidate-1",
            feasible=True,
            policy_allowed=True,
            risk_score=0.2,
            confidence_score=0.8,
            evidence_score=0.8,
            utility_score=0.7,
            reversibility_score=0.9,
            total_score=0.7,
            rejection_reasons=(
                CandidateRejectionReason.POLICY_VIOLATION,
            ),
        )


def test_select_action_requires_candidate() -> None:
    with pytest.raises(ValidationError):
        DecisionRecord(
            decision_id="decision-1",
            request_id="request-1",
            context_id="context-1",
            decision_kind=DecisionKind.NEXT_ACTION,
            disposition=DecisionDisposition.SELECT_ACTION,
            rationale="Select next action.",
            confidence=0.8,
            context_fingerprint="fingerprint-1",
        )


def test_no_safe_action_cannot_select_candidate() -> None:
    with pytest.raises(ValidationError):
        DecisionRecord(
            decision_id="decision-1",
            request_id="request-1",
            context_id="context-1",
            selected_candidate_id="candidate-1",
            decision_kind=DecisionKind.STOP,
            disposition=DecisionDisposition.NO_SAFE_ACTION,
            rationale="No candidate satisfies policy.",
            confidence=1.0,
            context_fingerprint="fingerprint-1",
        )
'@

Write-Host ""
Write-Host "M5.4 Package 0 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_decision_identifiers.py `
    .\tests\test_autonomous_decision_states.py `
    .\tests\test_autonomous_decision_policies.py `
    .\tests\test_autonomous_decision_models.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.4 Package 0 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M5.4 PACKAGE 0 COMPLETE" -ForegroundColor Green

git status --short