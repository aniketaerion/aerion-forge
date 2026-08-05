"""Telemetry for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from collections.abc import Mapping

from forge.agent_runtime.identifiers import agent_event_identifier
from forge.agent_runtime.models import (
    AgentEvent,
    AgentEventType,
)


def build_event(
    *,
    session_id: str,
    event_type: AgentEventType,
    message: str,
    stage_id: str | None = None,
    metadata: Mapping[str, str] | None = None,
) -> AgentEvent:
    payload = {
        "session_id": session_id,
        "event_type": event_type.value,
        "message": message,
        "stage_id": stage_id,
        "metadata": dict(metadata or {}),
    }

    return AgentEvent(
        event_id=agent_event_identifier(payload),
        session_id=session_id,
        event_type=event_type,
        message=message,
        stage_id=stage_id,
        metadata=dict(metadata or {}),
    )