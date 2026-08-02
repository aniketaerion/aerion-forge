"""Execution Controller validator tests."""

import pytest

from forge.execution_controller.errors import (
    ExecutionConfigurationError,
    ExecutionValidationError,
)
from forge.execution_controller.identifiers import (
    execution_request_fingerprint,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    ExecutionControllerConfiguration,
    ExecutionEvent,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionSession,
    ExecutionState,
    ExecutionStatistics,
    ExecutionTransition,
    OperationStatus,
)
from forge.execution_controller.validator import (
    ExecutionControllerValidator,
)


def _request(
    *,
    mission_id: str = "mission-123",
    task_ids: tuple[str, ...] = ("task-a",),
    requested_operations: tuple[str, ...] = ("edit",),
    dry_run: bool = True,
    source_fingerprints: dict[str, str] | None = None,
) -> ExecutionRequest:
    request = ExecutionRequest(
        request_id="execution-request-placeholder",
        request_fingerprint="placeholder",
        mission_id=mission_id,
        task_ids=task_ids,
        requested_operations=requested_operations,
        dry_run=dry_run,
        source_fingerprints=(
            source_fingerprints
            if source_fingerprints is not None
            else {
                "mission": "a" * 64,
                "tasks": "b" * 64,
            }
        ),
    )

    return request.model_copy(
        update={
            "request_fingerprint": (execution_request_fingerprint(request)),
        }
    )


def _approval(
    request: ExecutionRequest,
    *,
    decision: ApprovalDecision = ApprovalDecision.APPROVED,
    approved_operations: tuple[str, ...] = ("edit",),
) -> ApprovalRecord:
    return ApprovalRecord(
        approval_id="execution-approval-123",
        request_fingerprint=request.request_fingerprint,
        approver_id="engineering-lead",
        decision=decision,
        approved_operations=(approved_operations if decision is ApprovalDecision.APPROVED else ()),
        evidence_reference="approval.json",
    )


def _operation(
    *,
    task_id: str = "task-a",
    tool_id: str = "filesystem",
    operation_type: str = "edit",
    status: OperationStatus = OperationStatus.PENDING,
) -> ExecutionOperation:
    return ExecutionOperation(
        operation_id="execution-operation-123",
        task_id=task_id,
        tool_id=tool_id,
        operation_type=operation_type,
        arguments_fingerprint="c" * 64,
        status=status,
    )


def _statistics(
    operation_count: int = 0,
    *,
    pending_count: int = 0,
    running_count: int = 0,
    succeeded_count: int = 0,
    failed_count: int = 0,
    blocked_count: int = 0,
    cancelled_count: int = 0,
) -> ExecutionStatistics:
    return ExecutionStatistics(
        operation_count=operation_count,
        pending_count=pending_count,
        running_count=running_count,
        succeeded_count=succeeded_count,
        failed_count=failed_count,
        blocked_count=blocked_count,
        cancelled_count=cancelled_count,
    )


def test_valid_request_passes() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    assert result.valid is True
    assert result.findings == ()


def test_disabled_configuration_raises() -> None:
    with pytest.raises(ExecutionConfigurationError):
        ExecutionControllerValidator().validate_request(
            _request(),
            ExecutionControllerConfiguration(
                enabled=False,
            ),
            known_mission_id="mission-123",
            known_task_ids=("task-a",),
            required_source_fingerprints={},
        )


def test_mission_mismatch_is_error() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(mission_id="mission-other"),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is False
    assert {finding.code for finding in result.findings} == {"mission-id-mismatch"}


def test_unknown_task_is_error() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(task_ids=("task-missing",)),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is False
    assert result.findings[0].code == "unknown-task-ids"


def test_missing_source_fingerprint_is_error() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(source_fingerprints={}),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "a" * 64,
        },
    )

    assert result.valid is False
    assert result.findings[0].code == "missing-source-fingerprint"


def test_source_fingerprint_mismatch_is_error() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(
            source_fingerprints={
                "mission": "wrong",
            }
        ),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "a" * 64,
        },
    )

    assert result.valid is False
    assert result.findings[0].code == "source-fingerprint-mismatch"


def test_missing_operations_is_error() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(requested_operations=()),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is False
    assert result.findings[0].code == "missing-operations"


def test_missing_tasks_is_error() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(task_ids=()),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is False
    assert result.findings[0].code == "missing-tasks"


def test_non_dry_run_requires_dispatch_enabled() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(dry_run=False),
        ExecutionControllerConfiguration(
            allow_dispatch=False,
        ),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is False
    assert result.findings[0].code == "dispatch-disabled"


def test_non_dry_run_passes_when_dispatch_enabled() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(dry_run=False),
        ExecutionControllerConfiguration(
            allow_dispatch=True,
        ),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is True


def test_valid_approval_passes() -> None:
    request = _request()

    result = ExecutionControllerValidator().validate_approval_record(
        request,
        _approval(request),
        ExecutionControllerConfiguration(),
    )

    assert result.valid is True


def test_missing_approval_is_error() -> None:
    result = ExecutionControllerValidator().validate_approval_record(
        _request(),
        None,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert result.findings[0].code == "approval-invalid"


def test_approval_fingerprint_mismatch_is_error() -> None:
    request = _request()
    approval = _approval(request).model_copy(
        update={
            "request_fingerprint": "different",
        }
    )

    result = ExecutionControllerValidator().validate_approval_record(
        request,
        approval,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert result.findings[0].code == "approval-invalid"


def test_empty_approved_scope_is_error() -> None:
    request = _request()
    approval = _approval(
        request,
        approved_operations=(),
    )

    result = ExecutionControllerValidator().validate_approval_record(
        request,
        approval,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert result.findings[0].code == "approval-scope-empty"


def test_undeclared_approval_scope_is_error() -> None:
    request = _request()
    approval = _approval(
        request,
        approved_operations=("deploy",),
    )

    result = ExecutionControllerValidator().validate_approval_record(
        request,
        approval,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert result.findings[0].code == "approval-scope-mismatch"


def test_valid_operation_passes() -> None:
    request = _request()

    result = ExecutionControllerValidator().validate_operation(
        request,
        _approval(request),
        _operation(),
        frozenset({"filesystem"}),
    )

    assert result.valid is True


def test_unregistered_tool_is_error() -> None:
    request = _request()

    result = ExecutionControllerValidator().validate_operation(
        request,
        _approval(request),
        _operation(tool_id="unknown"),
        frozenset({"filesystem"}),
    )

    assert result.valid is False
    assert result.findings[0].code == "tool-not-registered"


def test_unapproved_operation_is_error() -> None:
    request = _request()

    result = ExecutionControllerValidator().validate_operation(
        request,
        _approval(request),
        _operation(operation_type="deploy"),
        frozenset({"filesystem"}),
    )

    assert result.valid is False
    assert any(finding.code == "operation-not-approved" for finding in result.findings)


def test_dry_run_rejects_succeeded_operation() -> None:
    request = _request(dry_run=True)

    result = ExecutionControllerValidator().validate_operation(
        request,
        _approval(request),
        _operation(status=OperationStatus.SUCCEEDED),
        frozenset({"filesystem"}),
    )

    assert result.valid is False
    assert any(finding.code == "dry-run-operation-status" for finding in result.findings)


def test_session_state_requiring_approval_is_error() -> None:
    session = ExecutionSession(
        session_id="execution-session-123",
        session_fingerprint="d" * 64,
        request=_request(),
        approval=None,
        current_state=ExecutionState.RUNNING,
        statistics=_statistics(),
    )

    result = ExecutionControllerValidator().validate_session(
        session,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert result.findings[0].code == "session-approval-missing"


def test_completed_session_with_pending_operation_is_error() -> None:
    request = _request()
    approval = _approval(request)
    operation = _operation()

    transition = ExecutionTransition(
        transition_id="execution-transition-123",
        previous_state=ExecutionState.RUNNING,
        event=ExecutionEvent.COMPLETE,
        next_state=ExecutionState.COMPLETED,
    )

    session = ExecutionSession(
        session_id="execution-session-123",
        session_fingerprint="d" * 64,
        request=request,
        approval=approval,
        current_state=ExecutionState.COMPLETED,
        transitions=(transition,),
        operations=(operation,),
        statistics=_statistics(
            operation_count=1,
            pending_count=1,
        ),
    )

    result = ExecutionControllerValidator().validate_session(
        session,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert any(finding.code == "completed-session-incomplete" for finding in result.findings)


def test_duplicate_transition_ids_are_error() -> None:
    request = _request()

    first = ExecutionTransition(
        transition_id="duplicate",
        previous_state=ExecutionState.REQUESTED,
        event=ExecutionEvent.VALIDATE,
        next_state=ExecutionState.VALIDATING,
    )
    second = ExecutionTransition(
        transition_id="duplicate",
        previous_state=ExecutionState.VALIDATING,
        event=ExecutionEvent.VALIDATION_PASSED,
        next_state=ExecutionState.AWAITING_APPROVAL,
    )

    session = ExecutionSession(
        session_id="execution-session-123",
        session_fingerprint="d" * 64,
        request=request,
        current_state=ExecutionState.AWAITING_APPROVAL,
        transitions=(first, second),
        statistics=_statistics(),
    )

    result = ExecutionControllerValidator().validate_session(
        session,
        ExecutionControllerConfiguration(),
    )

    assert result.valid is False
    assert result.findings[0].code == "duplicate-transition-ids"


def test_validate_or_raise_returns_valid_result() -> None:
    validator = ExecutionControllerValidator()
    result = validator.validate_request(
        _request(),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert validator.validate_or_raise(result) == result


def test_validate_or_raise_raises_for_invalid_result() -> None:
    validator = ExecutionControllerValidator()
    result = validator.validate_request(
        _request(task_ids=()),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    with pytest.raises(ExecutionValidationError):
        validator.validate_or_raise(result)


def test_findings_are_sorted_deterministically() -> None:
    result = ExecutionControllerValidator().validate_request(
        _request(
            mission_id="wrong",
            task_ids=(),
            requested_operations=(),
            source_fingerprints={},
        ),
        ExecutionControllerConfiguration(),
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "a" * 64,
        },
    )

    codes = [finding.code for finding in result.findings]

    assert codes == sorted(codes)
