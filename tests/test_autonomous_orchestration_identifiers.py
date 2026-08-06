from forge.autonomous_orchestration.identifiers import (
    mission_session_identifier,
    orchestration_request_identifier,
)


def test_orchestration_request_identifier_is_stable() -> None:
    first = orchestration_request_identifier(
        {
            "mission_id": "mission-1",
            "repository_root": "repository",
        }
    )
    second = orchestration_request_identifier(
        {
            "repository_root": "repository",
            "mission_id": "mission-1",
        }
    )

    assert first == second
    assert first.startswith("orchestration-request-")


def test_mission_session_identifier_has_prefix() -> None:
    result = mission_session_identifier(
        {
            "mission_id": "mission-1",
            "plan_id": "plan-1",
        }
    )

    assert result.startswith("mission-session-")