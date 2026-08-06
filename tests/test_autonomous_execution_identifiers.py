from forge.autonomous_execution.identifiers import (
    execution_request_identifier,
    tool_invocation_identifier,
)


def test_execution_request_identifier_is_stable() -> None:
    first = execution_request_identifier(
        {
            "mission_id": "mission-1",
            "step_id": "step-1",
        }
    )
    second = execution_request_identifier(
        {
            "step_id": "step-1",
            "mission_id": "mission-1",
        }
    )

    assert first == second
    assert first.startswith("execution-request-")


def test_tool_invocation_identifier_has_prefix() -> None:
    result = tool_invocation_identifier(
        {
            "mission_id": "mission-1",
            "tool_name": "ruff",
        }
    )

    assert result.startswith("tool-invocation-")