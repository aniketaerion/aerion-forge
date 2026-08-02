"""Execution Controller model tests."""

from types import MappingProxyType

import pytest
from pydantic import ValidationError

from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    EvidenceType,
    ExecutionControllerConfiguration,
    ExecutionEvent,
    ExecutionEvidence,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionSession,
    ExecutionState,
    ExecutionStatistics,
    ExecutionTransition,
    ExecutionValidationFinding,
    ExecutionValidationResult,
    OperationStatus,
)


def _request() -> ExecutionRequest:
    return ExecutionRequest(
        request_id="execution-request-1234567890",
        request_fingerprint="a" * 64,
        mission_id="mission-1234567890",
        task_ids=("task-b", "task-a"),
        requested_operations=("test", "edit"),
        dry_run=True,
        source_fingerprints={
            "mission": "b" * 64,
            "tasks": "c" * 64,
        },
    )


def _approval() -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="execution-approval-1234567890",
        request_fingerprint="a" * 64,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("test", "edit"),
        evidence_reference="approval-record.json",
    )


def _statistics(
    operation_count: int = 0,
) -> ExecutionStatistics:
    return ExecutionStatistics(
        operation_count=operation_count,
        pending_count=operation_count,
        running_count=0,
        succeeded_count=0,
        failed_count=0,
        blocked_count=0,
        cancelled_count=0,
    )


def _transition() -> ExecutionTransition:
    return ExecutionTransition(
        transition_id="execution-transition-1234567890",
        previous_state=ExecutionState.REQUESTED,
        event=ExecutionEvent.VALIDATE,
        next_state=ExecutionState.VALIDATING,
        evidence_ids=("evidence-b", "evidence-a"),
    )


def _operation() -> ExecutionOperation:
    return ExecutionOperation(
        operation_id="execution-operation-1234567890",
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="d" * 64,
        status=OperationStatus.PENDING,
    )


def _evidence() -> ExecutionEvidence:
    return ExecutionEvidence(
        evidence_id="execution-evidence-1234567890",
        evidence_type=EvidenceType.VALIDATION,
        source="execution-controller",
        fingerprint="e" * 64,
        reference="reports/validation.json",
        metadata={
            "z": "last",
            "a": "first",
        },
    )


def test_request_normalizes_task_ids() -> None:
    request = _request()

    assert request.task_ids == ("task-a", "task-b")


def test_request_normalizes_operations() -> None:
    request = _request()

    assert request.requested_operations == ("edit", "test")


def test_request_removes_blank_and_duplicate_values() -> None:
    request = ExecutionRequest(
        request_id="request",
        request_fingerprint="a" * 64,
        mission_id="mission",
        task_ids=("task-a", "", " task-a "),
        requested_operations=(" edit ", "", "edit"),
    )

    assert request.task_ids == ("task-a",)
    assert request.requested_operations == ("edit",)


def test_request_rejects_blank_identity() -> None:
    with pytest.raises(ValidationError):
        ExecutionRequest(
            request_id=" ",
            request_fingerprint="a" * 64,
            mission_id="mission",
        )


def test_request_source_mapping_is_immutable() -> None:
    request = _request()

    assert isinstance(
        request.source_fingerprints,
        MappingProxyType,
    )

    with pytest.raises(TypeError):
        request.source_fingerprints["new"] = "value"  # type: ignore[index]


def test_request_serializes_mapping_canonically() -> None:
    request = _request()
    payload = request.model_dump(mode="json")

    assert list(payload["source_fingerprints"]) == [
        "mission",
        "tasks",
    ]


def test_approval_normalizes_operations() -> None:
    approval = _approval()

    assert approval.approved_operations == (
        "edit",
        "test",
    )


def test_rejected_approval_cannot_approve_operations() -> None:
    with pytest.raises(ValidationError):
        ApprovalRecord(
            approval_id="approval",
            request_fingerprint="a" * 64,
            approver_id="lead",
            decision=ApprovalDecision.REJECTED,
            approved_operations=("edit",),
            evidence_reference="approval.json",
        )


def test_transition_normalizes_evidence_ids() -> None:
    transition = _transition()

    assert transition.evidence_ids == (
        "evidence-a",
        "evidence-b",
    )


def test_transition_normalizes_blank_reason() -> None:
    transition = ExecutionTransition(
        transition_id="transition",
        previous_state=ExecutionState.RUNNING,
        event=ExecutionEvent.FAIL,
        next_state=ExecutionState.FAILED,
        reason=" ",
    )

    assert transition.reason is None


def test_operation_rejects_blank_tool_id() -> None:
    with pytest.raises(ValidationError):
        ExecutionOperation(
            operation_id="operation",
            task_id="task",
            tool_id=" ",
            operation_type="edit",
            arguments_fingerprint="a" * 64,
        )


def test_evidence_metadata_is_immutable_and_sorted() -> None:
    evidence = _evidence()

    assert isinstance(evidence.metadata, MappingProxyType)
    assert list(evidence.model_dump(mode="json")["metadata"]) == ["a", "z"]


def test_statistics_accept_valid_counts() -> None:
    statistics = _statistics(2)

    assert statistics.operation_count == 2
    assert statistics.pending_count == 2


def test_statistics_reject_counts_above_total() -> None:
    with pytest.raises(ValidationError):
        ExecutionStatistics(
            operation_count=1,
            pending_count=1,
            running_count=1,
            succeeded_count=0,
            failed_count=0,
            blocked_count=0,
            cancelled_count=0,
        )


def test_session_accepts_matching_final_state() -> None:
    transition = _transition()

    session = ExecutionSession(
        session_id="execution-session-1234567890",
        session_fingerprint="f" * 64,
        request=_request(),
        current_state=ExecutionState.VALIDATING,
        transitions=(transition,),
        statistics=_statistics(),
    )

    assert session.current_state is ExecutionState.VALIDATING


def test_session_rejects_state_transition_mismatch() -> None:
    with pytest.raises(ValidationError):
        ExecutionSession(
            session_id="session",
            session_fingerprint="f" * 64,
            request=_request(),
            current_state=ExecutionState.REQUESTED,
            transitions=(_transition(),),
            statistics=_statistics(),
        )


def test_session_rejects_duplicate_operations() -> None:
    operation = _operation()

    with pytest.raises(ValidationError):
        ExecutionSession(
            session_id="session",
            session_fingerprint="f" * 64,
            request=_request(),
            current_state=ExecutionState.REQUESTED,
            operations=(operation, operation),
            statistics=_statistics(2),
        )


def test_session_rejects_duplicate_evidence() -> None:
    evidence = _evidence()

    with pytest.raises(ValidationError):
        ExecutionSession(
            session_id="session",
            session_fingerprint="f" * 64,
            request=_request(),
            current_state=ExecutionState.REQUESTED,
            evidence=(evidence, evidence),
            statistics=_statistics(),
        )


def test_session_rejects_operation_count_mismatch() -> None:
    with pytest.raises(ValidationError):
        ExecutionSession(
            session_id="session",
            session_fingerprint="f" * 64,
            request=_request(),
            current_state=ExecutionState.REQUESTED,
            operations=(_operation(),),
            statistics=_statistics(),
        )


def test_session_rejects_approval_fingerprint_mismatch() -> None:
    approval = _approval().model_copy(
        update={
            "request_fingerprint": "different",
        }
    )

    with pytest.raises(ValidationError):
        ExecutionSession(
            session_id="session",
            session_fingerprint="f" * 64,
            request=_request(),
            approval=approval,
            current_state=ExecutionState.APPROVED,
            statistics=_statistics(),
        )


def test_configuration_defaults_are_safe() -> None:
    configuration = ExecutionControllerConfiguration()

    assert configuration.enabled is True
    assert configuration.require_approval is True
    assert configuration.allow_dispatch is False
    assert configuration.history_limit == 20


def test_configuration_rejects_invalid_history_limit() -> None:
    with pytest.raises(ValidationError):
        ExecutionControllerConfiguration(
            history_limit=0,
        )


def test_validation_result_accepts_valid_result() -> None:
    result = ExecutionValidationResult(
        valid=True,
        findings=(),
    )

    assert result.valid is True


def test_valid_result_rejects_error_finding() -> None:
    with pytest.raises(ValidationError):
        ExecutionValidationResult(
            valid=True,
            findings=(
                ExecutionValidationFinding(
                    code="failure",
                    message="Failure occurred.",
                    is_error=True,
                ),
            ),
        )


def test_invalid_result_requires_error_finding() -> None:
    with pytest.raises(ValidationError):
        ExecutionValidationResult(
            valid=False,
            findings=(
                ExecutionValidationFinding(
                    code="warning",
                    message="Warning only.",
                    is_error=False,
                ),
            ),
        )


def test_models_are_frozen() -> None:
    request = _request()

    with pytest.raises(ValidationError):
        request.mission_id = "different"
