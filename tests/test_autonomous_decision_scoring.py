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