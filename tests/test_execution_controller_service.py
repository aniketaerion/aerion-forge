"""Execution Controller service tests."""

from pathlib import Path

import pytest

from forge.execution_controller.builder import (
    ExecutionControllerBuilder,
)
from forge.execution_controller.errors import (
    ExecutionValidationError,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    EvidenceType,
    ExecutionControllerConfiguration,
    ExecutionEvent,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionState,
    OperationStatus,
)
from forge.execution_controller.service import (
    ExecutionControllerService,
)


def _service(
    *,
    allow_dispatch: bool = False,
) -> ExecutionControllerService:
    return ExecutionControllerService(
        configuration=ExecutionControllerConfiguration(
            allow_dispatch=allow_dispatch,
        )
    )


def _request(
    service: ExecutionControllerService | None = None,
    *,
    dry_run: bool = True,
) -> ExecutionRequest:
    active = service or _service()

    return active.create_request(
        mission_id="mission-123",
        task_ids=("task-a",),
        requested_operations=("edit",),
        dry_run=dry_run,
        source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )


def _approval(
    service: ExecutionControllerService,
    request: ExecutionRequest,
) -> ApprovalRecord:
    return service.record_approval(
        request,
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("edit",),
        evidence_reference="approval.json",
    )


def _operation(
    request: ExecutionRequest,
    *,
    status: OperationStatus = OperationStatus.PENDING,
) -> ExecutionOperation:
    return ExecutionControllerBuilder().build_operation(
        request,
        task_id="task-a",
        tool_id="filesystem",
        operation_type="edit",
        arguments_fingerprint="c" * 64,
        status=status,
    )


def test_create_request_returns_deterministic_request() -> None:
    service = _service()

    first = _request(service)
    second = _request(service)

    assert first == second
    assert first.request_id == second.request_id


def test_validate_request_passes_for_matching_lineage() -> None:
    service = _service()
    request = _request(service)

    result = service.validate_request(
        request,
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={
            "mission": "a" * 64,
            "tasks": "b" * 64,
        },
    )

    assert result.valid is True


def test_validate_request_reports_mission_mismatch() -> None:
    service = _service()
    request = _request(service)

    result = service.validate_request(
        request,
        known_mission_id="mission-other",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is False


def test_validate_request_or_raise_returns_valid_result() -> None:
    service = _service()
    request = _request(service)

    result = service.validate_request_or_raise(
        request,
        known_mission_id="mission-123",
        known_task_ids=("task-a",),
        required_source_fingerprints={},
    )

    assert result.valid is True


def test_validate_request_or_raise_raises_for_invalid_request() -> None:
    service = _service()
    request = _request(service)

    with pytest.raises(ExecutionValidationError):
        service.validate_request_or_raise(
            request,
            known_mission_id="mission-other",
            known_task_ids=("task-a",),
            required_source_fingerprints={},
        )


def test_record_approval_preserves_request_fingerprint() -> None:
    service = _service()
    request = _request(service)

    approval = _approval(service, request)

    assert approval.request_fingerprint == request.request_fingerprint


def test_record_approval_rejects_empty_scope() -> None:
    service = _service()
    request = _request(service)

    with pytest.raises(ExecutionValidationError):
        service.record_approval(
            request,
            approver_id="engineering-lead",
            decision=ApprovalDecision.APPROVED,
            approved_operations=(),
            evidence_reference="approval.json",
        )


def test_create_session_without_approval_is_requested() -> None:
    service = _service()
    request = _request(service)

    session = service.create_session(request)

    assert session.current_state is ExecutionState.REQUESTED
    assert session.approval is None


def test_create_session_with_approval_is_approved() -> None:
    service = _service()
    request = _request(service)
    approval = _approval(service, request)

    session = service.create_session(
        request,
        approval=approval,
    )

    assert session.current_state is ExecutionState.APPROVED
    assert session.approval == approval


def test_create_session_rejects_mismatched_approval() -> None:
    service = _service()
    request = _request(service)

    approval = ApprovalRecord(
        approval_id="approval-mismatch",
        request_fingerprint="different",
        approver_id="engineering-lead",
        decision=ApprovalDecision.APPROVED,
        approved_operations=("edit",),
        evidence_reference="approval.json",
    )

    with pytest.raises(ExecutionValidationError):
        service.create_session(
            request,
            approval=approval,
        )


def test_transition_session_applies_valid_transition() -> None:
    service = _service()
    request = _request(service)
    approval = _approval(service, request)
    session = service.create_session(
        request,
        approval=approval,
    )

    updated = service.transition_session(
        session,
        ExecutionEvent.ENQUEUE,
    )

    assert updated.current_state is ExecutionState.QUEUED
    assert len(updated.transitions) == 1


def test_transition_session_preserves_original_session() -> None:
    service = _service()
    request = _request(service)
    approval = _approval(service, request)
    session = service.create_session(
        request,
        approval=approval,
    )

    updated = service.transition_session(
        session,
        ExecutionEvent.ENQUEUE,
    )

    assert session.current_state is ExecutionState.APPROVED
    assert session.transitions == ()
    assert updated is not session


def test_add_operation_requires_approval() -> None:
    service = _service()
    request = _request(service)
    session = service.create_session(request)

    with pytest.raises(ExecutionValidationError):
        service.add_operation(
            session,
            _operation(request),
            registered_tools=frozenset({"filesystem"}),
        )


def test_add_operation_accepts_registered_approved_operation() -> None:
    service = _service()
    request = _request(service)
    approval = _approval(service, request)
    session = service.create_session(
        request,
        approval=approval,
    )

    updated = service.add_operation(
        session,
        _operation(request),
        registered_tools=frozenset({"filesystem"}),
    )

    assert len(updated.operations) == 1
    assert updated.statistics.operation_count == 1


def test_add_operation_rejects_unregistered_tool() -> None:
    service = _service()
    request = _request(service)
    approval = _approval(service, request)
    session = service.create_session(
        request,
        approval=approval,
    )

    operation = _operation(request).model_copy(update={"tool_id": "unknown"})

    with pytest.raises(ExecutionValidationError):
        service.add_operation(
            session,
            operation,
            registered_tools=frozenset({"filesystem"}),
        )


def test_add_evidence_appends_evidence() -> None:
    service = _service()
    session = service.create_session(_request(service))

    updated = service.add_evidence(
        session,
        evidence_type=EvidenceType.VALIDATION,
        source="execution-controller",
        fingerprint="d" * 64,
        reference="validation.json",
        metadata={"result": "valid"},
    )

    assert len(updated.evidence) == 1
    assert updated.evidence[0].reference == "validation.json"


def test_replace_operations_recalculates_statistics() -> None:
    service = _service()
    request = _request(service)
    session = service.create_session(request)

    operation = _operation(
        request,
        status=OperationStatus.SUCCEEDED,
    )

    updated = service.replace_operations(
        session,
        (operation,),
    )

    assert updated.statistics.operation_count == 1
    assert updated.statistics.succeeded_count == 1


def test_validate_session_passes_for_requested_session() -> None:
    service = _service()
    session = service.create_session(_request(service))

    result = service.validate_session(session)

    assert result.valid is True


def test_validate_session_or_raise_rejects_running_without_approval() -> None:
    service = _service()
    request = _request(service)

    invalid = ExecutionControllerBuilder().build_session(
        request,
        current_state=ExecutionState.RUNNING,
    )

    with pytest.raises(ExecutionValidationError):
        service.validate_session_or_raise(invalid)


def test_render_reports_returns_complete_suite() -> None:
    service = _service()
    session = service.create_session(_request(service))

    reports = service.render_reports(session)

    assert set(reports) == {
        "EXECUTION_CONTROLLER.json",
        "EXECUTION_CONTROLLER_SUMMARY.json",
        "EXECUTION_CONTROLLER_EVIDENCE.json",
        "EXECUTION_CONTROLLER_TRANSITIONS.json",
        "EXECUTION_CONTROLLER.md",
    }


def test_render_reports_is_deterministic() -> None:
    service = _service()
    session = service.create_session(_request(service))

    first = service.render_reports(session)
    second = service.render_reports(session)

    assert first == second


def test_write_reports_creates_complete_suite(
    tmp_path: Path,
) -> None:
    service = _service()
    session = service.create_session(_request(service))

    paths = service.write_reports(
        session,
        tmp_path,
    )

    assert len(paths) == 5
    assert (tmp_path / "EXECUTION_CONTROLLER.json").is_file()


def test_service_uses_injected_builder() -> None:
    builder = ExecutionControllerBuilder()

    service = ExecutionControllerService(
        builder=builder,
    )

    assert service.builder is builder


def test_service_default_configuration_is_safe() -> None:
    service = ExecutionControllerService()

    assert service.configuration.require_approval is True
    assert service.configuration.allow_dispatch is False


def test_service_does_not_mutate_request() -> None:
    service = _service()
    request = _request(service)
    original = request.model_dump(mode="json")

    service.create_session(request)

    assert request.model_dump(mode="json") == original
