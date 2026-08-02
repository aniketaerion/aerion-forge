"""Execution Controller identifier and policy tests."""

import pytest

from forge.execution_controller.errors import (
    ExecutionApprovalMismatchError,
    ExecutionApprovalRejectedError,
    ExecutionApprovalRequiredError,
    ExecutionOperationNotApprovedError,
    ExecutionStateTransitionError,
    ExecutionToolNotRegisteredError,
)
from forge.execution_controller.identifiers import (
    approval_id,
    evidence_id,
    execution_request_fingerprint,
    execution_request_id,
    operation_fingerprint,
    operation_id,
    session_fingerprint,
    session_id,
    transition_id,
)
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
    OperationStatus,
)
from forge.execution_controller.policies import (
    is_terminal_state,
    resolve_next_state,
    validate_approval,
    validate_dispatch_allowed,
    validate_operation_scope,
    validate_registered_tool,
)


def _request() -> ExecutionRequest:
    request = ExecutionRequest(
        request_id="execution-request-placeholder",
        request_fingerprint="placeholder",
        mission_id="mission-123",
        task_ids=("task-b", "task-a"),
        requested_operations=("test", "edit"),
        dry_run=True,
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    fingerprint = execution_request_fingerprint(request)

    return request.model_copy(
        update={
            "request_fingerprint": fingerprint,
        }
    )


def _approval(
    request: ExecutionRequest,
    *,
    decision: ApprovalDecision = ApprovalDecision.APPROVED,
) -> ApprovalRecord:
    operations = request.requested_operations if decision is ApprovalDecision.APPROVED else ()

    return ApprovalRecord(
        approval_id="execution-approval-placeholder",
        request_fingerprint=request.request_fingerprint,
        approver_id="engineering-lead",
        decision=decision,
        approved_operations=operations,
        evidence_reference="approval.json",
    )


def _operation() -> ExecutionOperation:
    return ExecutionOperation(
        operation_id="execution-operation-placeholder",
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
        status=OperationStatus.PENDING,
    )


def _statistics() -> ExecutionStatistics:
    return ExecutionStatistics(
        operation_count=0,
        pending_count=0,
        running_count=0,
        succeeded_count=0,
        failed_count=0,
        blocked_count=0,
        cancelled_count=0,
    )


def test_request_id_is_deterministic() -> None:
    first = execution_request_id(
        "mission-123",
        ("task-b", "task-a"),
        ("test", "edit"),
        True,
        {
            "tasks": "b" * 64,
            "mission": "a" * 64,
        },
    )

    second = execution_request_id(
        "mission-123",
        ("task-a", "task-b"),
        ("edit", "test"),
        True,
        {
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    assert first == second


def test_request_id_changes_with_mission() -> None:
    first = execution_request_id(
        "mission-a",
        ("task-a",),
        ("edit",),
        True,
        {"mission": "a"},
    )
    second = execution_request_id(
        "mission-b",
        ("task-a",),
        ("edit",),
        True,
        {"mission": "a"},
    )

    assert first != second


def test_request_id_changes_with_dry_run() -> None:
    first = execution_request_id(
        "mission",
        ("task",),
        ("edit",),
        True,
        {"mission": "a"},
    )
    second = execution_request_id(
        "mission",
        ("task",),
        ("edit",),
        False,
        {"mission": "a"},
    )

    assert first != second


def test_request_fingerprint_is_repeatable() -> None:
    request = _request()

    assert execution_request_fingerprint(request) == execution_request_fingerprint(request)


def test_request_fingerprint_ignores_existing_fingerprint() -> None:
    request = _request()
    changed = request.model_copy(
        update={
            "request_fingerprint": "different",
        }
    )

    assert execution_request_fingerprint(request) == execution_request_fingerprint(changed)


def test_approval_id_is_deterministic() -> None:
    first = approval_id(
        "a" * 64,
        "lead",
        ("test", "edit"),
        "approval.json",
    )
    second = approval_id(
        "a" * 64,
        "lead",
        ("edit", "test"),
        "approval.json",
    )

    assert first == second


def test_approval_id_changes_with_approver() -> None:
    first = approval_id(
        "a" * 64,
        "lead-a",
        ("edit",),
        "approval.json",
    )
    second = approval_id(
        "a" * 64,
        "lead-b",
        ("edit",),
        "approval.json",
    )

    assert first != second


def test_operation_id_is_deterministic() -> None:
    first = operation_id(
        "request",
        "task",
        "filesystem",
        "edit",
        "a" * 64,
    )
    second = operation_id(
        "request",
        "task",
        "filesystem",
        "edit",
        "a" * 64,
    )

    assert first == second


def test_operation_id_changes_with_tool() -> None:
    first = operation_id(
        "request",
        "task",
        "filesystem",
        "edit",
        "a" * 64,
    )
    second = operation_id(
        "request",
        "task",
        "git",
        "edit",
        "a" * 64,
    )

    assert first != second


def test_transition_id_changes_with_ordinal() -> None:
    transition = ExecutionTransition(
        transition_id="placeholder",
        previous_state=ExecutionState.REQUESTED,
        event=ExecutionEvent.VALIDATE,
        next_state=ExecutionState.VALIDATING,
    )

    first = transition_id(
        "session",
        transition,
        1,
    )
    second = transition_id(
        "session",
        transition,
        2,
    )

    assert first != second


def test_evidence_id_is_deterministic() -> None:
    evidence = ExecutionEvidence(
        evidence_id="placeholder",
        evidence_type=EvidenceType.VALIDATION,
        source="controller",
        fingerprint="a" * 64,
        reference="validation.json",
    )

    assert evidence_id("session", evidence) == evidence_id("session", evidence)


def test_session_id_uses_request_and_approval() -> None:
    request = _request()
    approval = _approval(request)

    with_approval = session_id(
        request,
        approval,
    )
    without_approval = session_id(
        request,
        None,
    )

    assert with_approval != without_approval


def test_session_fingerprint_is_repeatable() -> None:
    request = _request()
    session = ExecutionSession(
        session_id="session",
        session_fingerprint="placeholder",
        request=request,
        current_state=ExecutionState.REQUESTED,
        statistics=_statistics(),
    )

    assert session_fingerprint(session) == session_fingerprint(session)


def test_session_fingerprint_ignores_existing_value() -> None:
    request = _request()
    first = ExecutionSession(
        session_id="session",
        session_fingerprint="first",
        request=request,
        current_state=ExecutionState.REQUESTED,
        statistics=_statistics(),
    )
    second = first.model_copy(
        update={
            "session_fingerprint": "second",
        }
    )

    assert session_fingerprint(first) == session_fingerprint(second)


def test_operation_fingerprint_is_repeatable() -> None:
    operation = _operation()

    assert operation_fingerprint(operation) == operation_fingerprint(operation)


@pytest.mark.parametrize(
    ("state", "expected"),
    [
        (ExecutionState.COMPLETED, True),
        (ExecutionState.FAILED, True),
        (ExecutionState.CANCELLED, True),
        (ExecutionState.VALIDATION_FAILED, True),
        (ExecutionState.APPROVAL_REJECTED, True),
        (ExecutionState.RUNNING, False),
        (ExecutionState.REQUESTED, False),
    ],
)
def test_terminal_state_policy(
    state: ExecutionState,
    expected: bool,
) -> None:
    assert is_terminal_state(state) is expected


def test_resolve_valid_transition() -> None:
    result = resolve_next_state(
        ExecutionState.REQUESTED,
        ExecutionEvent.VALIDATE,
    )

    assert result is ExecutionState.VALIDATING


def test_reject_illegal_transition() -> None:
    with pytest.raises(ExecutionStateTransitionError):
        resolve_next_state(
            ExecutionState.REQUESTED,
            ExecutionEvent.COMPLETE,
        )


def test_terminal_state_rejects_transition() -> None:
    with pytest.raises(ExecutionStateTransitionError):
        resolve_next_state(
            ExecutionState.COMPLETED,
            ExecutionEvent.START,
        )


def test_approval_is_required_by_default() -> None:
    with pytest.raises(ExecutionApprovalRequiredError):
        validate_approval(
            _request(),
            None,
            ExecutionControllerConfiguration(),
        )


def test_approval_can_be_disabled_by_configuration() -> None:
    validate_approval(
        _request(),
        None,
        ExecutionControllerConfiguration(
            require_approval=False,
        ),
    )


def test_approval_rejects_fingerprint_mismatch() -> None:
    request = _request()
    approval = _approval(request).model_copy(
        update={
            "request_fingerprint": "different",
        }
    )

    with pytest.raises(ExecutionApprovalMismatchError):
        validate_approval(
            request,
            approval,
            ExecutionControllerConfiguration(),
        )


def test_rejected_approval_stops_execution() -> None:
    request = _request()

    with pytest.raises(ExecutionApprovalRejectedError):
        validate_approval(
            request,
            _approval(
                request,
                decision=ApprovalDecision.REJECTED,
            ),
            ExecutionControllerConfiguration(),
        )


def test_operation_scope_accepts_valid_operation() -> None:
    request = _request()

    validate_operation_scope(
        request,
        _approval(request),
        _operation(),
    )


def test_operation_scope_rejects_undeclared_operation() -> None:
    request = _request()
    operation = _operation().model_copy(
        update={
            "operation_type": "deploy",
        }
    )

    with pytest.raises(ExecutionOperationNotApprovedError):
        validate_operation_scope(
            request,
            _approval(request),
            operation,
        )


def test_operation_scope_rejects_unknown_task() -> None:
    request = _request()
    operation = _operation().model_copy(
        update={
            "task_id": "task-missing",
        }
    )

    with pytest.raises(ExecutionOperationNotApprovedError):
        validate_operation_scope(
            request,
            _approval(request),
            operation,
        )


def test_registered_tool_accepts_known_tool() -> None:
    validate_registered_tool(
        _operation(),
        frozenset({"filesystem"}),
    )


def test_registered_tool_rejects_unknown_tool() -> None:
    with pytest.raises(ExecutionToolNotRegisteredError):
        validate_registered_tool(
            _operation(),
            frozenset({"git"}),
        )


def test_dispatch_disabled_by_default() -> None:
    with pytest.raises(ExecutionToolNotRegisteredError):
        validate_dispatch_allowed(ExecutionControllerConfiguration())


def test_dispatch_allowed_when_enabled() -> None:
    validate_dispatch_allowed(
        ExecutionControllerConfiguration(
            allow_dispatch=True,
        )
    )
