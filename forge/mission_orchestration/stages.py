"""Built-in stage definitions for M3.6 Mission Orchestration."""

from __future__ import annotations

from forge.mission_orchestration.models import StageDefinition, StageType


def builtin_stage_definitions() -> tuple[StageDefinition, ...]:
    """Return the deterministic built-in mission workflow stages."""
    return (
        StageDefinition(
            stage_id="mission_validation",
            stage_type=StageType.MISSION_VALIDATION,
            name="Mission validation",
        ),
        StageDefinition(
            stage_id="execution_request",
            stage_type=StageType.EXECUTION_REQUEST,
            name="Execution request",
            dependencies=("mission_validation",),
        ),
        StageDefinition(
            stage_id="safe_change_plan",
            stage_type=StageType.SAFE_CHANGE_PLAN,
            name="Safe change plan",
            dependencies=("execution_request",),
        ),
        StageDefinition(
            stage_id="impact_assessment",
            stage_type=StageType.IMPACT_ASSESSMENT,
            name="Impact assessment",
            dependencies=("safe_change_plan",),
        ),
        StageDefinition(
            stage_id="approval_gate",
            stage_type=StageType.APPROVAL_GATE,
            name="Approval gate",
            dependencies=("impact_assessment",),
            approval_required=True,
        ),
        StageDefinition(
            stage_id="safe_edit_dry_run",
            stage_type=StageType.SAFE_EDIT_DRY_RUN,
            name="Safe edit dry-run",
            dependencies=("approval_gate",),
        ),
        StageDefinition(
            stage_id="safe_edit_apply",
            stage_type=StageType.SAFE_EDIT_APPLY,
            name="Safe edit apply",
            dependencies=("safe_edit_dry_run",),
            approval_required=True,
        ),
        StageDefinition(
            stage_id="validation",
            stage_type=StageType.VALIDATION,
            name="Validation",
            dependencies=("safe_edit_apply",),
        ),
        StageDefinition(
            stage_id="autonomous_repair",
            stage_type=StageType.AUTONOMOUS_REPAIR,
            name="Autonomous repair",
            dependencies=("validation",),
            optional=True,
            max_attempts=3,
        ),
        StageDefinition(
            stage_id="final_validation",
            stage_type=StageType.FINAL_VALIDATION,
            name="Final validation",
            dependencies=("validation", "autonomous_repair"),
        ),
        StageDefinition(
            stage_id="mission_reporting",
            stage_type=StageType.MISSION_REPORTING,
            name="Mission reporting",
            dependencies=("final_validation",),
        ),
    )