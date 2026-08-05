from forge.agent_runtime.identifiers import (
    agent_request_identifier,
    agent_session_identifier,
    stable_identifier,
)


def test_stable_identifier_is_deterministic() -> None:
    first = stable_identifier(
        "sample",
        {"objective": "build", "paths": ["b.py", "a.py"]},
    )
    second = stable_identifier(
        "sample",
        {"paths": ["b.py", "a.py"], "objective": "build"},
    )

    assert first == second
    assert first.startswith("sample-")


def test_request_identifier_changes_with_objective() -> None:
    first = agent_request_identifier({"objective": "one"})
    second = agent_request_identifier({"objective": "two"})

    assert first != second


def test_session_identifier_has_expected_prefix() -> None:
    identifier = agent_session_identifier(
        {"request_id": "request-1", "revision": "abc"}
    )

    assert identifier.startswith("agent-session-")