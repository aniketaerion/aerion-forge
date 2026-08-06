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