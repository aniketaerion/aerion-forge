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