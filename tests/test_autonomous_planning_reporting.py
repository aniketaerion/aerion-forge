import json

from forge.autonomous_planning.models import (
    PlanningPlan,
    PlanningStep,
    PlanningValidationResult,
)
from forge.autonomous_planning.reporting import (
    PlanningReport,
    planning_report_json,
    planning_report_markdown,
)
from forge.autonomous_planning.states import StepKind


def report() -> PlanningReport:
    plan = PlanningPlan(
        plan_id="plan-1",
        request_id="request-1",
        summary="Repository-grounded plan.",
        steps=(
            PlanningStep(
                step_id="step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                kind=StepKind.VALIDATION,
            ),
        ),
    )
    validation = PlanningValidationResult(
        plan_id=plan.plan_id,
        valid=True,
    )
    return PlanningReport(
        plan=plan,
        validation=validation,
    )


def test_json_report_is_serializable() -> None:
    payload = json.loads(
        planning_report_json(report())
    )

    assert payload["step_count"] == 1
    assert payload["plan"]["plan_id"] == "plan-1"


def test_markdown_report_contains_plan() -> None:
    markdown = planning_report_markdown(report())

    assert "# Autonomous Planning Report" in markdown
    assert "plan-1" in markdown
    assert "Validate" in markdown