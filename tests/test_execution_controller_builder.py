"""Execution Controller builder tests."""

import pytest

from forge.execution_controller.builder import (
    ExecutionControllerBuilder,
)
from forge.execution_controller.errors import (
    ExecutionStateTransitionError,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    EvidenceType,
    ExecutionEvent,
    ExecutionRequest,
    ExecutionState,
    OperationStatus,
)


def _builder() -> ExecutionControllerBuilder:
    return ExecutionControllerBuilder()


def _request() -> ExecutionRequest:
    return _builder().build_request(
        mission_id="mission-123",
        task_ids=("task-b", "task-a"),
        requested_operations=("test", "edit"),
        dry_run=True,
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )


def _approval() -> ApprovalRecord:
    request = _request()

    return _builder().build_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("test", "edit"),
        evidence_reference="approval.json",
    )


def test_build_request_creates_deterministic_identity() -> None:
    first = _request()
    second = _request()

    assert first == second
    assert first.request_id == second.request_id
    assert first.request_fingerprint == second.request_fingerprint


def test_build_request_normalizes_sequences() -> None:
    request = _request()

    assert request.task_ids == ("task-a", "task-b")
    assert request.requested_operations == (
        "edit",
        "test",
    )


def test_build_request_changes_with_mission() -> None:
    first = _request()

    second = _builder().build_request(
        mission_id="mission-other",
        task_ids=("task-a", "task-b"),
        requested_operations=("edit", "test"),
        dry_run=True,
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    assert first.request_id != second.request_id


def test_build_request_changes_with_dry_run() -> None:
    first = _request()

    second = _builder().build_request(
        mission_id="mission-123",
        task_ids=("task-a", "task-b"),
        requested_operations=("edit", "test"),
        dry_run=False,
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    assert first.request_id != second.request_id


def test_build_approval_preserves_request_lineage() -> None:
    request = _request()
    approval = _builder().build_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("edit",),
        evidence_reference="approval.json",
    )

    assert approval.request_fingerprint == request.request_fingerprint
    assert approval.approved_operations == ("edit",)


def test_rejected_approval_has_empty_scope() -> None:
    request = _request()

    approval = _builder().build_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.REJECTED,
        approved_operations=("edit",),
        evidence_reference="rejection.json",
    )

    assert approval.approved_operations == ()


def test_build_approval_is_deterministic() -> None:
    request = _request()

    first = _builder().build_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("test", "edit"),
        evidence_reference="approval.json",
    )
    second = _builder().build_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("edit", "test"),
        evidence_reference="approval.json",
    )

    assert first == second


def test_build_operation_creates_identity() -> None:
    request = _request()

    operation = _builder().build_operation(
        request,
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
    )

    assert operation.operation_id.startswith("execution-operation-")
    assert operation.status is OperationStatus.PENDING


def test_build_operation_is_deterministic() -> None:
    request = _request()
    builder = _builder()

    first = builder.build_operation(
        request,
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
    )
    second = builder.build_operation(
        request,
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
    )

    assert first == second


def test_build_evidence_is_deterministic() -> None:
    builder = _builder()

    first = builder.build_evidence(
        session_id_value="session-123",
        evidence_type=EvidenceType.VALIDATION,
        source="controller",
        fingerprint="d" * 64,
        reference="validation.json",
        metadata={"b": "2", "a": "1"},
    )
    second = builder.build_evidence(
        session_id_value="session-123",
        evidence_type=EvidenceType.VALIDATION,
        source="controller",
        fingerprint="d" * 64,
        reference="validation.json",
        metadata={"a": "1", "b": "2"},
    )

    assert first == second


def test_build_transition_resolves_next_state() -> None:
    transition = _builder().build_transition(
        session_id_value="session-123",
        current_state=ExecutionState.REQUESTED,
        event=ExecutionEvent.VALIDATE,
        ordinal=1,
    )

    assert transition.next_state is ExecutionState.VALIDATING


def test_build_transition_rejects_illegal_event() -> None:
    with pytest.raises(ExecutionStateTransitionError):
        _builder().build_transition(
            session_id_value="session-123",
            current_state=ExecutionState.REQUESTED,
            event=ExecutionEvent.COMPLETE,
            ordinal=1,
        )


def test_build_session_defaults_to_requested() -> None:
    session = _builder().build_session(_request())

    assert session.current_state is ExecutionState.REQUESTED
    assert session.statistics.operation_count == 0


def test_build_session_is_deterministic() -> None:
    request = _request()
    builder = _builder()

    first = builder.build_session(request)
    second = builder.build_session(request)

    assert first == second
    assert first.session_fingerprint == second.session_fingerprint


def test_session_with_approval_has_distinct_identity() -> None:
    request = _request()
    builder = _builder()

    without_approval = builder.build_session(request)
    with_approval = builder.build_session(
        request,
        approval=_approval(),
        current_state=ExecutionState.APPROVED,
    )

    assert without_approval.session_id != with_approval.session_id


def test_transition_session_appends_transition() -> None:
    builder = _builder()
    session = builder.build_session(_request())

    updated = builder.transition_session(
        session,
        ExecutionEvent.VALIDATE,
    )

    assert updated.current_state is ExecutionState.VALIDATING
    assert len(updated.transitions) == 1


def test_transition_session_preserves_request() -> None:
    builder = _builder()
    session = builder.build_session(_request())

    updated = builder.transition_session(
        session,
        ExecutionEvent.VALIDATE,
    )

    assert updated.request == session.request


def test_replace_operations_updates_statistics() -> None:
    builder = _builder()
    request = _request()
    session = builder.build_session(request)

    operation = builder.build_operation(
        request,
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
        status=OperationStatus.SUCCEEDED,
    )

    updated = builder.replace_operations(
        session,
        (operation,),
    )

    assert updated.statistics.operation_count == 1
    assert updated.statistics.succeeded_count == 1
    assert updated.statistics.pending_count == 0


def test_pending_statistics_include_approved_and_queued() -> None:
    builder = _builder()
    request = _request()
    session = builder.build_session(request)

    operations = tuple(
        builder.build_operation(
            request,
            task_id="task-a",
            tool_id="filesystem",
            operation_type="edit",
            arguments_fingerprint=str(index) * 64,
            status=status,
        )
        for index, status in enumerate(
            (
                OperationStatus.PENDING,
                OperationStatus.APPROVED,
                OperationStatus.QUEUED,
            ),
            start=1,
        )
    )

    updated = builder.replace_operations(
        session,
        operations,
    )

    assert updated.statistics.operation_count == 3
    assert updated.statistics.pending_count == 3


def test_append_evidence_preserves_existing_evidence() -> None:
    builder = _builder()
    session = builder.build_session(_request())

    first = builder.build_evidence(
        session_id_value=session.session_id,
        evidence_type=EvidenceType.VALIDATION,
        source="controller",
        fingerprint="a" * 64,
        reference="first.json",
    )
    second = builder.build_evidence(
        session_id_value=session.session_id,
        evidence_type=EvidenceType.REPORT,
        source="controller",
        fingerprint="b" * 64,
        reference="second.json",
    )

    updated = builder.append_evidence(
        builder.append_evidence(session, first),
        second,
    )

    assert updated.evidence == (first, second)


def test_builder_does_not_mutate_original_session() -> None:
    builder = _builder()
    session = builder.build_session(_request())

    updated = builder.transition_session(
        session,
        ExecutionEvent.VALIDATE,
    )

    assert session.current_state is ExecutionState.REQUESTED
    assert session.transitions == ()
    assert updated is not session
