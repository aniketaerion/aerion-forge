"""Capability-adapter contracts for M3.8 Unified Agent Runtime."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from forge.agent_runtime.errors import AgentRuntimeCapabilityError
from forge.agent_runtime.models import (
    AgentCapability,
    AgentSession,
    AgentStage,
    AgentStageResult,
    AgentStageStatus,
)

CapabilityExecutor = Callable[
    [Path, AgentSession, AgentStage, Mapping[str, Any]],
    AgentStageResult,
]


class AgentCapabilityAdapter(ABC):
    """Common runtime interface for one existing Forge capability."""

    capability: AgentCapability

    @abstractmethod
    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        """Execute one capability-backed runtime stage."""

    def validate_stage(self, stage: AgentStage) -> None:
        """Ensure the stage is assigned to this adapter."""
        if stage.capability is not self.capability:
            raise AgentRuntimeCapabilityError(
                "adapter capability mismatch: "
                f"expected {self.capability.value}, "
                f"received {stage.capability.value}"
            )


class CallbackCapabilityAdapter(AgentCapabilityAdapter):
    """Safe dependency-injection adapter for a native Forge service."""

    def __init__(self, executor: CapabilityExecutor) -> None:
        self._executor = executor

    def execute(
        self,
        repository_root: Path,
        session: AgentSession,
        stage: AgentStage,
        context: Mapping[str, Any],
    ) -> AgentStageResult:
        self.validate_stage(stage)
        result = self._executor(
            repository_root.resolve(),
            session,
            stage,
            context,
        )

        if result.stage_id != stage.stage_id:
            raise AgentRuntimeCapabilityError(
                "capability adapter returned a result for another stage"
            )

        return result


def succeeded_result(
    stage: AgentStage,
    summary: str,
    *,
    artifact_paths: tuple[str, ...] = (),
    evidence: Mapping[str, str] | None = None,
    started_at: datetime | None = None,
) -> AgentStageResult:
    """Create a normalized successful runtime-stage result."""
    return AgentStageResult(
        stage_id=stage.stage_id,
        status=AgentStageStatus.SUCCEEDED,
        summary=summary,
        artifact_paths=artifact_paths,
        evidence=dict(evidence or {}),
        started_at=started_at or datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )


def failed_result(
    stage: AgentStage,
    summary: str,
    *,
    evidence: Mapping[str, str] | None = None,
    started_at: datetime | None = None,
) -> AgentStageResult:
    """Create a normalized failed runtime-stage result."""
    return AgentStageResult(
        stage_id=stage.stage_id,
        status=AgentStageStatus.FAILED,
        summary=summary,
        evidence=dict(evidence or {}),
        started_at=started_at or datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )