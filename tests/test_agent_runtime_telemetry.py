from forge.agent_runtime.models import AgentEventType
from forge.agent_runtime.telemetry import build_event


def test_event_identifier_is_deterministic() -> None:
    first = build_event(
        session_id="session-1",
        event_type=AgentEventType.SESSION_CREATED,
        message="created",
    )
    second = build_event(
        session_id="session-1",
        event_type=AgentEventType.SESSION_CREATED,
        message="created",
    )

    assert first.event_id == second.event_id