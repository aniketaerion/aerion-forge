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