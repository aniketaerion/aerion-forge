"""Immutable contracts for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from forge.mission_runtime.errors import MissionContractError
from forge.mission_runtime.states import (
    MissionApprovalDecision,
    MissionApprovalKind,
    MissionEvidenceKind,
    MissionResultStatus,
    MissionRisk,
    MissionState,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class MissionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    request_id: str
    workspace_id: str
    repository_root: str
    statement: str
    requested_by: str
    risk_tolerance: MissionRisk = MissionRisk.MEDIUM
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_request(self) -> MissionRequest:
        if not self.workspace_id.strip():
            raise MissionContractError(
                "Workspace ID cannot be empty."
            )
        if not self.repository_root.strip():
            raise MissionContractError(
                "Repository root cannot be empty."
            )
        if not self.statement.strip():
            raise MissionContractError(
                "Mission statement cannot be empty."
            )
        if not self.requested_by.strip():
            raise MissionContractError(
                "Mission requester cannot be empty."
            )
        return self


class MissionApproval(BaseModel):
    model_config = ConfigDict(frozen=True)

    approval_id: str
    session_id: str
    kind: MissionApprovalKind
    decision: MissionApprovalDecision
    decided_by: str | None = None
    rationale: str | None = None
    scope: tuple[str, ...] = ()
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_approval(self) -> MissionApproval:
        if (
            self.decision
            is not MissionApprovalDecision.PENDING
            and not self.decided_by
        ):
            raise MissionContractError(
                "Decided approval requires an approver."
            )
        if (
            self.decision
            is not MissionApprovalDecision.PENDING
            and not self.rationale
        ):
            raise MissionContractError(
                "Decided approval requires rationale."
            )
        return self


class MissionCheckpoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    checkpoint_id: str
    session_id: str
    state: MissionState
    repository_fingerprint: str
    planning_plan_id: str | None = None
    execution_run_id: str | None = None
    created_at: datetime = Field(default_factory=utc_now)


class MissionEvidence(BaseModel):
    model_config = ConfigDict(frozen=True)

    evidence_id: str
    session_id: str
    kind: MissionEvidenceKind
    references: tuple[str, ...]
    summary: str
    created_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_evidence(self) -> MissionEvidence:
        if not self.references:
            raise MissionContractError(
                "Mission evidence requires references."
            )
        if not self.summary.strip():
            raise MissionContractError(
                "Mission evidence summary cannot be empty."
            )
        return self


class MissionSession(BaseModel):
    model_config = ConfigDict(frozen=True)

    session_id: str
    request_id: str
    workspace_id: str
    repository_root: str
    repository_fingerprint: str
    state: MissionState = MissionState.CREATED
    detected_technologies: tuple[str, ...] = ()
    selected_capabilities: tuple[str, ...] = ()
    memory_query_ids: tuple[str, ...] = ()
    planning_request_id: str | None = None
    planning_plan_id: str | None = None
    plan_approval_id: str | None = None
    execution_run_ids: tuple[str, ...] = ()
    verification_references: tuple[str, ...] = ()
    documentation_references: tuple[str, ...] = ()
    review_package_reference: str | None = None
    final_approval_id: str | None = None
    recovery_count: int = Field(default=0, ge=0)
    failure_reason: str | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_session(self) -> MissionSession:
        if not self.repository_root.strip():
            raise MissionContractError(
                "Mission repository root cannot be empty."
            )
        if not self.repository_fingerprint.strip():
            raise MissionContractError(
                "Repository fingerprint cannot be empty."
            )
        if (
            self.state is MissionState.COMPLETED
            and not self.verification_references
        ):
            raise MissionContractError(
                "Completed mission requires verification evidence."
            )
        return self


class MissionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    result_id: str
    session_id: str
    status: MissionResultStatus
    summary: str
    evidence_ids: tuple[str, ...] = ()
    review_package_reference: str | None = None
    completed_at: datetime = Field(default_factory=utc_now)

    @model_validator(mode="after")
    def validate_result(self) -> MissionResult:
        if not self.summary.strip():
            raise MissionContractError(
                "Mission result summary cannot be empty."
            )
        return self