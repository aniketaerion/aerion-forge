"""Immutable contracts for autonomous mission orchestration."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.autonomous_orchestration.states import (
    RESUMABLE_ORCHESTRATION_STATES,
    TERMINAL_ORCHESTRATION_STATES,
    IterationOutcome,
    OrchestrationState,
    OrchestrationStopKind,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class FrozenOrchestrationContract(BaseModel):
    """Base immutable orchestration contract."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class OrchestrationRequest(FrozenOrchestrationContract):
    """Request to start or simulate mission orchestration."""

    request_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    repository_root: str = Field(min_length=1)
    dry_run: bool = True
    maximum_cycles: int = Field(default=25, ge=1, le=500)
    requested_by: str = Field(min_length=1)
    created_at: datetime = Field(default_factory=utc_now)


class MissionSession(FrozenOrchestrationContract):
    """Versioned state of one mission-orchestration session."""

    session_id: str = Field(min_length=1)
    schema_version: str = "1.0"
    mission_id: str = Field(min_length=1)
    plan_id: str = Field(min_length=1)
    plan_version: int = Field(ge=1)
    repository_root: str = Field(min_length=1)
    state: OrchestrationState = OrchestrationState.CREATED
    current_step_id: str | None = None
    completed_step_ids: tuple[str, ...] = ()
    failed_step_ids: tuple[str, ...] = ()
    cycle_count: int = Field(default=0, ge=0)
    execution_count: int = Field(default=0, ge=0)
    retry_count: int = Field(default=0, ge=0)
    rollback_count: int = Field(default=0, ge=0)
    replan_count: int = Field(default=0, ge=0)
    checkpoint_id: str | None = None
    stop_reason: str | None = None
    version: int = Field(default=1, ge=1)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_session_invariants(
        self,
    ) -> MissionSession:
        completed = set(self.completed_step_ids)
        failed = set(self.failed_step_ids)

        if len(completed) != len(self.completed_step_ids):
            raise ValueError(
                "completed_step_ids cannot contain duplicates."
            )

        if len(failed) != len(self.failed_step_ids):
            raise ValueError(
                "failed_step_ids cannot contain duplicates."
            )

        overlap = completed.intersection(failed)
        if overlap:
            raise ValueError(
                "A step cannot be both completed and failed."
            )

        if (
            self.current_step_id is not None
            and self.current_step_id in completed
        ):
            raise ValueError(
                "Current step cannot already be completed."
            )

        if (
            self.state in TERMINAL_ORCHESTRATION_STATES
            and self.stop_reason is None
        ):
            raise ValueError(
                "Terminal orchestration session requires stop_reason."
            )

        return self


class OrchestrationIteration(FrozenOrchestrationContract):
    """Immutable record of one bounded orchestration iteration."""

    iteration_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    sequence: int = Field(ge=1)
    mission_version_before: int = Field(ge=1)
    mission_version_after: int | None = Field(default=None, ge=1)
    selected_step_id: str | None = None
    execution_request_id: str | None = None
    execution_id: str | None = None
    outcome: IterationOutcome
    recovery_action: str | None = None
    evidence_ids: tuple[str, ...] = ()
    event_ids: tuple[str, ...] = ()
    started_at: datetime = Field(default_factory=utc_now)
    completed_at: datetime | None = None

    @model_validator(mode="after")
    def validate_iteration_execution_limit(
        self,
    ) -> OrchestrationIteration:
        if (
            self.execution_id is not None
            and self.execution_request_id is None
        ):
            raise ValueError(
                "Execution result requires an execution request."
            )

        if (
            self.outcome
            in {
                IterationOutcome.STEP_SUCCEEDED,
                IterationOutcome.STEP_FAILED,
                IterationOutcome.DRY_RUN_COMPLETED,
            }
            and self.execution_id is None
        ):
            raise ValueError(
                "Execution outcome requires execution_id."
            )

        return self


class SessionCheckpoint(FrozenOrchestrationContract):
    """Restart-safe orchestration session checkpoint."""

    checkpoint_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    mission_id: str = Field(min_length=1)
    session_version: int = Field(ge=1)
    mission_snapshot_version: int = Field(ge=1)
    plan_version: int = Field(ge=1)
    repository_fingerprint: str = Field(min_length=1)
    current_step_id: str | None = None
    completed_step_ids: tuple[str, ...] = ()
    verified: bool = False
    created_at: datetime = Field(default_factory=utc_now)


class OrchestrationStop(FrozenOrchestrationContract):
    """Explicit reason the orchestrator stopped."""

    stop_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    stop_kind: OrchestrationStopKind
    reason: str = Field(min_length=1)
    approval_required: bool = False
    resumable: bool = False
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_resumability(
        self,
    ) -> OrchestrationStop:
        if (
            self.stop_kind
            in {
                OrchestrationStopKind.COMPLETED,
                OrchestrationStopKind.FAILED,
                OrchestrationStopKind.CANCELLED,
            }
            and self.resumable
        ):
            raise ValueError(
                "Terminal orchestration stops cannot be resumable."
            )

        return self


def session_is_resumable(
    session: MissionSession,
) -> bool:
    """Return whether the session state may enter resume validation."""
    return session.state in RESUMABLE_ORCHESTRATION_STATES