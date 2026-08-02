"""Execution Controller domain models."""

from collections.abc import Mapping
from enum import StrEnum
from types import MappingProxyType
from typing import Annotated, TypeAlias

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = "1.0"


def _serialize_string_mapping(
    value: Mapping[str, str],
) -> dict[str, str]:
    return {key: value[key] for key in sorted(value)}


SerializableStringMapping: TypeAlias = Annotated[
    Mapping[str, str],
    PlainSerializer(
        _serialize_string_mapping,
        return_type=dict[str, str],
        when_used="always",
    ),
]


class FrozenModel(BaseModel):
    """Strict immutable execution model."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
    )


class ExecutionState(StrEnum):
    REQUESTED = "requested"
    VALIDATING = "validating"
    VALIDATION_FAILED = "validation_failed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVAL_REJECTED = "approval_rejected"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    BLOCKED = "blocked"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    FAILED = "failed"
    COMPLETED = "completed"


class ExecutionEvent(StrEnum):
    VALIDATE = "validate"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"
    APPROVE = "approve"
    REJECT = "reject"
    ENQUEUE = "enqueue"
    START = "start"
    BLOCKING_CONDITION = "blocking_condition"
    FAIL = "fail"
    COMPLETE = "complete"
    CANCEL = "cancel"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLATION_COMPLETE = "cancellation_complete"


class ApprovalDecision(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"


class OperationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    BLOCKED = "blocked"
    CANCELLED = "cancelled"


class EvidenceType(StrEnum):
    APPROVAL = "approval"
    VALIDATION = "validation"
    TOOL_REQUEST = "tool_request"
    TOOL_RESULT = "tool_result"
    FAILURE = "failure"
    CANCELLATION = "cancellation"
    REPORT = "report"


class ExecutionFailureCategory(StrEnum):
    VALIDATION = "validation"
    APPROVAL = "approval"
    TRANSITION = "transition"
    TOOL = "tool"
    PERSISTENCE = "persistence"
    REPORTING = "reporting"
    CANCELLATION = "cancellation"
    UNKNOWN = "unknown"


class ExecutionRequest(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    request_id: str
    request_fingerprint: str
    mission_id: str
    task_ids: tuple[str, ...] = ()
    requested_operations: tuple[str, ...] = ()
    dry_run: bool = True
    source_fingerprints: SerializableStringMapping = Field(default_factory=dict)

    @field_validator(
        "request_id",
        "request_fingerprint",
        "mission_id",
    )
    @classmethod
    def reject_blank_identity(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Execution request identity fields cannot be blank.")
        return normalized

    @field_validator(
        "task_ids",
        "requested_operations",
    )
    @classmethod
    def normalize_sequences(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        normalized = tuple(sorted({item.strip() for item in value if item.strip()}))
        return normalized

    @field_validator("source_fingerprints")
    @classmethod
    def normalize_source_fingerprints(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        normalized = {
            key.strip(): item.strip() for key, item in value.items() if key.strip() and item.strip()
        }
        return MappingProxyType({key: normalized[key] for key in sorted(normalized)})


class ApprovalRecord(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    approval_id: str
    request_fingerprint: str
    approver_id: str
    decision: ApprovalDecision
    approved_operations: tuple[str, ...] = ()
    evidence_reference: str

    @field_validator(
        "approval_id",
        "request_fingerprint",
        "approver_id",
        "evidence_reference",
    )
    @classmethod
    def reject_blank_text(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Approval identity and evidence fields cannot be blank.")
        return normalized

    @field_validator("approved_operations")
    @classmethod
    def normalize_approved_operations(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({item.strip() for item in value if item.strip()}))

    @model_validator(mode="after")
    def validate_decision_scope(self) -> "ApprovalRecord":
        if self.decision is ApprovalDecision.REJECTED and self.approved_operations:
            raise ValueError("Rejected approval cannot contain approved operations.")
        return self


class ExecutionTransition(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    transition_id: str
    previous_state: ExecutionState
    event: ExecutionEvent
    next_state: ExecutionState
    reason: str | None = None
    evidence_ids: tuple[str, ...] = ()

    @field_validator("transition_id")
    @classmethod
    def reject_blank_transition_id(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Transition ID cannot be blank.")
        return normalized

    @field_validator("reason")
    @classmethod
    def normalize_reason(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("evidence_ids")
    @classmethod
    def normalize_evidence_ids(
        cls,
        value: tuple[str, ...],
    ) -> tuple[str, ...]:
        return tuple(sorted({item.strip() for item in value if item.strip()}))


class ExecutionOperation(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    operation_id: str
    task_id: str
    tool_id: str
    operation_type: str
    arguments_fingerprint: str
    status: OperationStatus = OperationStatus.PENDING
    result_reference: str | None = None
    failure_reference: str | None = None

    @field_validator(
        "operation_id",
        "task_id",
        "tool_id",
        "operation_type",
        "arguments_fingerprint",
    )
    @classmethod
    def reject_blank_operation_fields(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Execution operation fields cannot be blank.")
        return normalized


class ExecutionEvidence(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    evidence_id: str
    evidence_type: EvidenceType
    source: str
    fingerprint: str
    reference: str
    metadata: SerializableStringMapping = Field(default_factory=dict)

    @field_validator(
        "evidence_id",
        "source",
        "fingerprint",
        "reference",
    )
    @classmethod
    def reject_blank_evidence_fields(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Execution evidence fields cannot be blank.")
        return normalized

    @field_validator("metadata")
    @classmethod
    def normalize_metadata(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        normalized = {
            key.strip(): item.strip() for key, item in value.items() if key.strip() and item.strip()
        }
        return MappingProxyType({key: normalized[key] for key in sorted(normalized)})


class ExecutionStatistics(FrozenModel):
    operation_count: int = Field(ge=0)
    pending_count: int = Field(ge=0)
    running_count: int = Field(ge=0)
    succeeded_count: int = Field(ge=0)
    failed_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    cancelled_count: int = Field(ge=0)

    @model_validator(mode="after")
    def validate_counts(self) -> "ExecutionStatistics":
        counted = (
            self.pending_count
            + self.running_count
            + self.succeeded_count
            + self.failed_count
            + self.blocked_count
            + self.cancelled_count
        )
        if counted > self.operation_count:
            raise ValueError("Execution statistics counts exceed operation count.")
        return self


class ExecutionSession(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    session_id: str
    session_fingerprint: str
    request: ExecutionRequest
    approval: ApprovalRecord | None = None
    current_state: ExecutionState
    transitions: tuple[ExecutionTransition, ...] = ()
    operations: tuple[ExecutionOperation, ...] = ()
    evidence: tuple[ExecutionEvidence, ...] = ()
    statistics: ExecutionStatistics
    source_fingerprints: SerializableStringMapping = Field(default_factory=dict)

    @field_validator(
        "session_id",
        "session_fingerprint",
    )
    @classmethod
    def reject_blank_session_fields(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Execution session identity fields cannot be blank.")
        return normalized

    @field_validator("source_fingerprints")
    @classmethod
    def normalize_source_fingerprints(
        cls,
        value: Mapping[str, str],
    ) -> Mapping[str, str]:
        normalized = {
            key.strip(): item.strip() for key, item in value.items() if key.strip() and item.strip()
        }
        return MappingProxyType({key: normalized[key] for key in sorted(normalized)})

    @model_validator(mode="after")
    def validate_session(self) -> "ExecutionSession":
        if self.transitions:
            latest = self.transitions[-1]
            if latest.next_state is not self.current_state:
                raise ValueError("Current state must match final transition state.")

        operation_ids = [operation.operation_id for operation in self.operations]
        if len(operation_ids) != len(set(operation_ids)):
            raise ValueError("Execution operation IDs must be unique.")

        evidence_ids = [evidence.evidence_id for evidence in self.evidence]
        if len(evidence_ids) != len(set(evidence_ids)):
            raise ValueError("Execution evidence IDs must be unique.")

        if self.statistics.operation_count != len(self.operations):
            raise ValueError("Execution statistics operation count mismatch.")

        if (
            self.approval is not None
            and self.approval.request_fingerprint != self.request.request_fingerprint
        ):
            raise ValueError("Approval does not match execution request.")

        return self


class ExecutionStore(FrozenModel):
    schema_version: str = SCHEMA_VERSION
    sessions: dict[str, ExecutionSession] = Field(default_factory=dict)
    history: dict[str, list[ExecutionSession]] = Field(default_factory=dict)


class ExecutionControllerConfiguration(FrozenModel):
    enabled: bool = True
    strict_validation: bool = True
    require_approval: bool = True
    allow_dispatch: bool = False
    history_limit: int = Field(default=20, ge=1, le=1000)


class ExecutionValidationFinding(FrozenModel):
    code: str
    message: str
    is_error: bool

    @field_validator("code", "message")
    @classmethod
    def reject_blank_finding_fields(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Validation finding fields cannot be blank.")
        return normalized


class ExecutionValidationResult(FrozenModel):
    valid: bool
    findings: tuple[ExecutionValidationFinding, ...] = ()

    @model_validator(mode="after")
    def validate_consistency(
        self,
    ) -> "ExecutionValidationResult":
        has_errors = any(finding.is_error for finding in self.findings)
        if self.valid and has_errors:
            raise ValueError("Valid result cannot contain error findings.")
        if not self.valid and not has_errors:
            raise ValueError("Invalid result must contain an error finding.")
        return self
