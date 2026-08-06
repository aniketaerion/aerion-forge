"""Mission-session progress evaluation."""

from __future__ import annotations

from dataclasses import dataclass

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_runtime.models import MissionPlan


@dataclass(frozen=True, slots=True)
class MissionProgress:
    """Deterministic progress snapshot."""

    total_steps: int
    completed_steps: int
    failed_steps: int
    remaining_steps: int
    completion_percent: float
    complete: bool


def evaluate_progress(
    session: MissionSession,
    plan: MissionPlan,
) -> MissionProgress:
    """Evaluate mission completion from session and plan state."""
    plan_step_ids = {step.step_id for step in plan.steps}
    completed = plan_step_ids.intersection(session.completed_step_ids)
    failed = plan_step_ids.intersection(session.failed_step_ids)
    total = len(plan_step_ids)
    remaining = total - len(completed)

    percentage = (
        100.0
        if total == 0
        else round((len(completed) / total) * 100.0, 2)
    )

    return MissionProgress(
        total_steps=total,
        completed_steps=len(completed),
        failed_steps=len(failed),
        remaining_steps=remaining,
        completion_percent=percentage,
        complete=remaining == 0 and not failed,
    )