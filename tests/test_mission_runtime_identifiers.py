from forge.mission_runtime.identifiers import (
    mission_request_identifier,
    mission_session_identifier,
)


def test_mission_identifiers_are_deterministic() -> None:
    payload = {
        "workspace_id": "workspace-1",
        "paths": {"b.py", "a.py"},
    }

    assert mission_request_identifier(
        payload
    ) == mission_request_identifier(payload)


def test_mission_identifier_prefixes_are_distinct() -> None:
    payload = {"mission": "complete procurement"}

    assert mission_request_identifier(
        payload
    ).startswith("mission-request-")

    assert mission_session_identifier(
        payload
    ).startswith("mission-session-")