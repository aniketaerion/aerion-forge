"""CLI commands for M5.7 autonomous execution."""

from __future__ import annotations

import json

import typer

from forge.autonomous_execution_v2.history import ExecutionHistory
from forge.autonomous_execution_v2.models import (
    ExecutionRun,
    ExecutionStep,
)
from forge.autonomous_execution_v2.policies import (
    AutonomousExecutionV2Policy,
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

app = typer.Typer(
    help="Inspect and simulate M5.7 autonomous execution."
)


def _sample_run() -> ExecutionRun:
    return ExecutionRun(
        run_id="execution-run-v2-simulation",
        request_id="execution-request-v2-simulation",
        plan_id="planning-plan-simulation",
        plan_version=1,
        repository_root="simulation-repository",
        repository_fingerprint="simulation-fingerprint",
        state=ExecutionRunState.SUCCEEDED,
        steps=(
            ExecutionStep(
                step_id="execution-step-v2-validate",
                planning_step_id="planning-step-validate",
                sequence=1,
                name="Validate",
                description="Run controlled repository validation.",
                state=ExecutionStepState.SUCCEEDED,
                required_tools=("test",),
                expected_outputs=("validation-results",),
                acceptance_criteria=("Validation passes.",),
            ),
        ),
    )


@app.command("simulate")
def simulate(
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
) -> None:
    """Render a deterministic execution simulation."""
    run = _sample_run()
    history = ExecutionHistory(
        run=run,
        attempts=(),
        evidence=(),
        recovery_decisions=(),
    )
    report = ExecutionReport(
        run=run,
        history=history,
    )

    if output_format == "markdown":
        typer.echo(execution_report_markdown(report))
        return

    if output_format != "json":
        raise typer.BadParameter(
            "Format must be 'json' or 'markdown'."
        )

    typer.echo(execution_report_json(report))


@app.command("status")
def status() -> None:
    """Show a deterministic execution status sample."""
    run = _sample_run()
    typer.echo(
        json.dumps(
            {
                "run_id": run.run_id,
                "state": run.state.value,
                "step_count": len(run.steps),
                "completed_steps": sum(
                    1
                    for step in run.steps
                    if step.state
                    is ExecutionStepState.SUCCEEDED
                ),
            },
            indent=2,
            sort_keys=True,
        )
    )


@app.command("policy")
def policy() -> None:
    """Show the default M5.7 execution policy."""
    typer.echo(
        json.dumps(
            AutonomousExecutionV2Policy().model_dump(
                mode="json"
            ),
            indent=2,
            sort_keys=True,
        )
    )