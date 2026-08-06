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