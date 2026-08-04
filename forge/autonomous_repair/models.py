"""Immutable contracts for M3.5 Autonomous Repair."""

from __future__ import annotations

from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, model_validator


class FrozenModel(BaseModel):
    """Base class for immutable repair contracts."""

    model_config = ConfigDict(frozen=True, extra="forbid")


class RepairProviderType(StrEnum):
    """Supported repair providers."""

    EXACT_PATCH = "exact_patch"
    RUFF_FIX = "ruff_fix"


class RepairPatchOperation(StrEnum):
    """Supported bounded patch operations."""

    INSERT = "insert"
    REPLACE = "replace"
    DELETE = "delete"


class RepairExecutionStatus(StrEnum):
    """Autonomous repair state."""

    CREATED = "created"
    VALIDATED = "validated"
    PROPOSED = "proposed"
    DRY_RUN_COMPLETE = "dry_run_complete"
    AWAITING_APPROVAL = "awaiting_approval"
    APPLYING = "applying"
    REVALIDATING = "revalidating"
    SUCCEEDED = "succeeded"
    ROLLING_BACK = "rolling_back"
    RETRY_READY = "retry_ready"
    FAILED = "failed"


def _relative_path(value: str) -> str:
    normalized = value.replace("\\", "/").strip()
    path = PurePosixPath(normalized)
    if not normalized or path.is_absolute() or ".." in path.parts:
        raise ValueError("path must be repository-relative without traversal")
    return path.as_posix()


class RepairApproval(FrozenModel):
    """Explicit human approval evidence."""

    approved: bool = False
    approved_by: str | None = None
    reason: str | None = None

    @model_validator(mode="after")
    def validate_approval(self) -> RepairApproval:
        if self.approved and not self.approved_by:
            raise ValueError("approved repairs require approved_by")
        return self


class RepairInput(FrozenModel):
    """Input derived from an M3.4 repair candidate."""

    input_id: str
    candidate_id: str
    repository_root: str
    provider: RepairProviderType
    finding_ids: tuple[str, ...]
    target_paths: tuple[str, ...]
    repository_fingerprint: str
    objective: str

    @model_validator(mode="after")
    def validate_input(self) -> RepairInput:
        if not self.finding_ids:
            raise ValueError("repair input requires findings")
        if not self.target_paths:
            raise ValueError("repair input requires target paths")
        normalized = tuple(_relative_path(path) for path in self.target_paths)
        if len(normalized) != len(set(normalized)):
            raise ValueError("duplicate target paths are not allowed")
        object.__setattr__(self, "target_paths", normalized)
        return self


class RepairPatch(FrozenModel):
    """One bounded file patch."""

    patch_id: str
    relative_path: str
    operation: RepairPatchOperation
    start_offset: Annotated[int, Field(ge=0)]
    end_offset: Annotated[int, Field(ge=0)]
    expected_text: str = ""
    replacement_text: str = ""
    source_fingerprint: str

    @model_validator(mode="after")
    def validate_patch(self) -> RepairPatch:
        object.__setattr__(self, "relative_path", _relative_path(self.relative_path))
        if self.end_offset < self.start_offset:
            raise ValueError("end_offset may not precede start_offset")
        if self.operation is RepairPatchOperation.INSERT:
            if self.start_offset != self.end_offset:
                raise ValueError("INSERT requires equal offsets")
            if self.expected_text:
                raise ValueError("INSERT must not include expected_text")
        if self.operation is RepairPatchOperation.DELETE:
            if not self.expected_text:
                raise ValueError("DELETE requires expected_text")
            if self.replacement_text:
                raise ValueError("DELETE requires empty replacement_text")
        if self.operation is RepairPatchOperation.REPLACE and not self.expected_text:
            raise ValueError("REPLACE requires expected_text")
        return self


class RepairProposal(FrozenModel):
    """Provider-generated bounded repair proposal."""

    proposal_id: str
    input_id: str
    provider: RepairProviderType
    patches: tuple[RepairPatch, ...]
    affected_paths: tuple[str, ...]
    risk_notes: tuple[str, ...] = ()
    validation_commands: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_proposal(self) -> RepairProposal:
        if not self.patches:
            raise ValueError("repair proposal requires at least one patch")
        normalized = tuple(_relative_path(path) for path in self.affected_paths)
        patch_paths = {patch.relative_path for patch in self.patches}
        if patch_paths != set(normalized):
            raise ValueError("affected_paths must match patch target paths")
        object.__setattr__(self, "affected_paths", normalized)
        return self


class RepairExecutionRequest(FrozenModel):
    """Dry-run or approved execution request."""

    request_id: str
    proposal: RepairProposal
    repository_root: str
    repository_fingerprint: str
    dry_run: bool = True
    approval: RepairApproval = RepairApproval()

    @model_validator(mode="after")
    def validate_execution_request(self) -> RepairExecutionRequest:
        if not self.dry_run and not self.approval.approved:
            raise ValueError("apply mode requires explicit approval")
        return self


class RepairValidationEvidence(FrozenModel):
    """Validation evidence before or after a repair."""

    stage: str
    passed: bool
    tool_results: tuple[str, ...] = ()
    finding_ids: tuple[str, ...] = ()


class RepairExecutionAttempt(FrozenModel):
    """One bounded autonomous-repair attempt."""

    attempt_number: Annotated[int, Field(ge=1)]
    proposal_id: str
    status: RepairExecutionStatus
    dry_run_request_id: str | None = None
    apply_request_id: str | None = None
    validation_evidence: tuple[RepairValidationEvidence, ...] = ()
    errors: tuple[str, ...] = ()


class RepairExecutionSession(FrozenModel):
    """Bounded repair execution session."""

    session_id: str
    input: RepairInput
    max_attempts: Annotated[int, Field(ge=1, le=10)]
    status: RepairExecutionStatus = RepairExecutionStatus.CREATED
    attempts: tuple[RepairExecutionAttempt, ...] = ()

    @model_validator(mode="after")
    def validate_attempt_limit(self) -> RepairExecutionSession:
        if len(self.attempts) > self.max_attempts:
            raise ValueError("attempt count exceeds max_attempts")
        return self


class RepairExecutionReport(FrozenModel):
    """Final auditable autonomous-repair report."""

    session_id: str
    status: RepairExecutionStatus
    succeeded: bool
    attempts: tuple[RepairExecutionAttempt, ...]
    final_repository_fingerprint: str | None = None
    messages: tuple[str, ...] = ()