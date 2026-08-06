from forge.autonomous_runtime.risk import (
    classify_action_risk,
    maximum_risk,
)
from forge.autonomous_runtime.states import RiskClass


def test_known_action_risk_is_classified() -> None:
    assert (
        classify_action_risk("create_release")
        is RiskClass.R4_CRITICAL
    )


def test_unknown_action_defaults_high() -> None:
    assert (
        classify_action_risk("unknown_action")
        is RiskClass.R3_HIGH
    )


def test_maximum_risk_returns_highest_value() -> None:
    assert maximum_risk(
        (
            RiskClass.R1_LOW,
            RiskClass.R4_CRITICAL,
            RiskClass.R2_MODERATE,
        )
    ) is RiskClass.R4_CRITICAL