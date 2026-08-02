"""Execution Controller approval and state-transition policies."""

from collections.abc import Mapping

from forge.execution_controller.errors import (
    ExecutionApprovalMismatchError,
    ExecutionApprovalRejectedError,
    ExecutionApprovalRequiredError,
    ExecutionOperationNotApprovedError,
    ExecutionStateTransitionError,
    ExecutionToolNotRegisteredError,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    ExecutionControllerConfiguration,
    ExecutionEvent,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionState,
)

TERMINAL_STATES = frozenset(
    {
        ExecutionState.VALIDATION_FAILED,
        ExecutionState.APPROVAL_REJECTED,
        ExecutionState.CANCELLED,
        ExecutionState.FAILED,
        ExecutionState.COMPLETED,
    }
)

ALLOWED_TRANSITIONS: Mapping[
    tuple[ExecutionState, ExecutionEvent],
    ExecutionState,
] = {
    (
        ExecutionState.REQUESTED,
        ExecutionEvent.VALIDATE,
    ): ExecutionState.VALIDATING,
    (
        ExecutionState.VALIDATING,
        ExecutionEvent.VALIDATION_PASSED,
    ): ExecutionState.AWAITING_APPROVAL,
    (
        ExecutionState.VALIDATING,
        ExecutionEvent.VALIDATION_FAILED,
    ): ExecutionState.VALIDATION_FAILED,
    (
        ExecutionState.AWAITING_APPROVAL,
        ExecutionEvent.APPROVE,
    ): ExecutionState.APPROVED,
    (
        ExecutionState.AWAITING_APPROVAL,
        ExecutionEvent.REJECT,
    ): ExecutionState.APPROVAL_REJECTED,
    (
        ExecutionState.APPROVED,
        ExecutionEvent.ENQUEUE,
    ): ExecutionState.QUEUED,
    (
        ExecutionState.QUEUED,
        ExecutionEvent.START,
    ): ExecutionState.RUNNING,
    (
        ExecutionState.RUNNING,
        ExecutionEvent.BLOCKING_CONDITION,
    ): ExecutionState.BLOCKED,
    (
        ExecutionState.RUNNING,
        ExecutionEvent.FAIL,
    ): ExecutionState.FAILED,
    (
        ExecutionState.RUNNING,
        ExecutionEvent.COMPLETE,
    ): ExecutionState.COMPLETED,
    (
        ExecutionState.RUNNING,
        ExecutionEvent.CANCEL_REQUESTED,
    ): ExecutionState.CANCELLING,
    (
        ExecutionState.CANCELLING,
        ExecutionEvent.CANCELLATION_COMPLETE,
    ): ExecutionState.CANCELLED,
    (
        ExecutionState.REQUESTED,
        ExecutionEvent.CANCEL,
    ): ExecutionState.CANCELLED,
    (
        ExecutionState.AWAITING_APPROVAL,
        ExecutionEvent.CANCEL,
    ): ExecutionState.CANCELLED,
    (
        ExecutionState.APPROVED,
        ExecutionEvent.CANCEL,
    ): ExecutionState.CANCELLED,
    (
        ExecutionState.QUEUED,
        ExecutionEvent.CANCEL,
    ): ExecutionState.CANCELLED,
}


def is_terminal_state(
    state: ExecutionState,
) -> bool:
    return state in TERMINAL_STATES


def resolve_next_state(
    current_state: ExecutionState,
    event: ExecutionEvent,
) -> ExecutionState:
    if is_terminal_state(current_state):
        raise ExecutionStateTransitionError("Terminal execution state cannot transition further.")

    key = (current_state, event)

    if key not in ALLOWED_TRANSITIONS:
        raise ExecutionStateTransitionError(
            f"Illegal execution transition: {current_state.value} + {event.value}"
        )

    return ALLOWED_TRANSITIONS[key]


def validate_approval(
    request: ExecutionRequest,
    approval: ApprovalRecord | None,
    configuration: ExecutionControllerConfiguration,
) -> None:
    if not configuration.require_approval:
        return

    if approval is None:
        raise ExecutionApprovalRequiredError("Explicit approval is required before execution.")

    if approval.request_fingerprint != request.request_fingerprint:
        raise ExecutionApprovalMismatchError("Approval request fingerprint does not match.")

    if approval.decision is ApprovalDecision.REJECTED:
        raise ExecutionApprovalRejectedError("Execution request was rejected.")


def validate_operation_scope(
    request: ExecutionRequest,
    approval: ApprovalRecord,
    operation: ExecutionOperation,
) -> None:
    if operation.operation_type not in (request.requested_operations):
        raise ExecutionOperationNotApprovedError("Operation was not declared in the request.")

    if operation.operation_type not in (approval.approved_operations):
        raise ExecutionOperationNotApprovedError("Operation is outside approved scope.")

    if operation.task_id not in request.task_ids:
        raise ExecutionOperationNotApprovedError("Operation task is outside request scope.")


def validate_registered_tool(
    operation: ExecutionOperation,
    registered_tools: frozenset[str],
) -> None:
    if operation.tool_id not in registered_tools:
        raise ExecutionToolNotRegisteredError(f"Tool is not registered: {operation.tool_id}")


def validate_dispatch_allowed(
    configuration: ExecutionControllerConfiguration,
) -> None:
    if not configuration.allow_dispatch:
        raise ExecutionToolNotRegisteredError("Tool dispatch is disabled by configuration.")
