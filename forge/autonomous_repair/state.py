"""State machine for M3.5 Autonomous Repair."""

from __future__ import annotations

from forge.autonomous_repair.errors import RepairExecutionError
from forge.autonomous_repair.models import RepairExecutionStatus

_ALLOWED_TRANSITIONS: dict[
    RepairExecutionStatus,
    frozenset[RepairExecutionStatus],
] = {
    RepairExecutionStatus.CREATED: frozenset(
        {RepairExecutionStatus.VALIDATED, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.VALIDATED: frozenset(
        {RepairExecutionStatus.PROPOSED, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.PROPOSED: frozenset(
        {RepairExecutionStatus.DRY_RUN_COMPLETE, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.DRY_RUN_COMPLETE: frozenset(
        {
            RepairExecutionStatus.AWAITING_APPROVAL,
            RepairExecutionStatus.APPLYING,
            RepairExecutionStatus.FAILED,
        }
    ),
    RepairExecutionStatus.AWAITING_APPROVAL: frozenset(
        {RepairExecutionStatus.APPLYING, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.APPLYING: frozenset(
        {
            RepairExecutionStatus.REVALIDATING,
            RepairExecutionStatus.ROLLING_BACK,
            RepairExecutionStatus.FAILED,
        }
    ),
    RepairExecutionStatus.REVALIDATING: frozenset(
        {
            RepairExecutionStatus.SUCCEEDED,
            RepairExecutionStatus.ROLLING_BACK,
            RepairExecutionStatus.FAILED,
        }
    ),
    RepairExecutionStatus.ROLLING_BACK: frozenset(
        {RepairExecutionStatus.RETRY_READY, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.RETRY_READY: frozenset(
        {RepairExecutionStatus.VALIDATED, RepairExecutionStatus.FAILED}
    ),
    RepairExecutionStatus.SUCCEEDED: frozenset(),
    RepairExecutionStatus.FAILED: frozenset(),
}


def can_transition(
    current: RepairExecutionStatus,
    target: RepairExecutionStatus,
) -> bool:
    """Return whether a state transition is permitted."""
    return target in _ALLOWED_TRANSITIONS[current]


def transition(
    current: RepairExecutionStatus,
    target: RepairExecutionStatus,
) -> RepairExecutionStatus:
    """Validate and return the target state."""
    if not can_transition(current, target):
        raise RepairExecutionError(
            f"invalid autonomous-repair transition: {current.value} -> {target.value}"
        )
    return target