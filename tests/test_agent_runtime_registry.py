from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.errors import AgentRuntimeCapabilityError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentObjective,
    AgentRuntimeRequest,
    AgentSession,
    AgentSessionStatus,
    AgentStage,
    AgentStageResult,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry


def executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, Any],
) -> AgentStageResult:
    del repository_root, session, context
    return succeeded_result(stage, "planned")


def test_registry_returns_registered_adapter() -> None:
    adapter = PlanningAdapter(executor)
    registry = AgentCapabilityRegistry((adapter,))

    assert registry.get(AgentCapability.MISSION_PLANNING) is adapter


def test_registry_rejects_duplicate_capability() -> None:
    adapter = PlanningAdapter(executor)

    with pytest.raises(AgentRuntimeCapabilityError):
        AgentCapabilityRegistry((adapter, adapter))


def test_registry_reports_missing_required_capability() -> None:
    registry = AgentCapabilityRegistry()

    with pytest.raises(AgentRuntimeCapabilityError):
        registry.validate_required(
            (AgentCapability.MISSION_PLANNING,)
        )


def test_adapter_rejects_capability_mismatch() -> None:
    adapter = PlanningAdapter(executor)
    objective = AgentObjective(
        objective="Implement feature",
        repository_root=".",
    )
    request = AgentRuntimeRequest(
        request_id="request-1",
        objective=objective,
    )
    stage = AgentStage(
        stage_id="stage-1",
        sequence=1,
        capability=AgentCapability.IMPACT_ANALYSIS,
        name="Impact",
    )
    session = AgentSession(
        session_id="session-1",
        request=request,
        status=AgentSessionStatus.CREATED,
        stages=(stage,),
    )

    with pytest.raises(AgentRuntimeCapabilityError):
        adapter.execute(Path.cwd(), session, stage, {})