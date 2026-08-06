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