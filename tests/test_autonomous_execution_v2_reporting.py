import json

from forge.autonomous_execution_v2.history import ExecutionHistory
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.reporting import (
    ExecutionReport,
    execution_report_json,
    execution_report_markdown,
)
from forge.autonomous_execution_v2.states import (
    ExecutionRunState,
    ExecutionStepState,
)


def report() -> ExecutionReport:
    run = ExecutionRun(
        run_id="run-1",
        request_id="request-1",
        plan_id="plan-1",
        plan_version=1,
        repository_root="repository",
        repository_fingerprint="fingerprint",
        state=ExecutionRunState.SUCCEEDED,
        steps=(
            ExecutionStep(
                step_id="step-1",
                planning_step_id="planning-step-1",
                sequence=1,
                name="Validate",
                description="Validate repository behaviour.",
                state=ExecutionStepState.SUCCEEDED,
            ),
        ),
    )
    history = ExecutionHistory(
        run=run,
        attempts=(),
        evidence=(),
        recovery_decisions=(),
    )
    return ExecutionReport(
        run=run,
        history=history,
    )


def test_json_report_is_serializable() -> None:
    payload = json.loads(
        execution_report_json(report())
    )

    assert payload["run"]["run_id"] == "run-1"
    assert payload["summary"]["step_count"] == 1
    assert payload["summary"]["succeeded_steps"] == 1


def test_markdown_report_contains_execution_details() -> None:
    markdown = execution_report_markdown(report())

    assert "# Autonomous Execution Report" in markdown
    assert "run-1" in markdown
    assert "Validate" in markdown