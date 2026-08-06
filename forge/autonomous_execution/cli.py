"""Read-only CLI for the M5.2 autonomous execution engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_execution.models import (
    ExecutionRequest,
    StepExecutionRecord,
    utc_now,
)
from forge.autonomous_execution.reporting import (
    execution_summary,
    write_execution_report,
)
from forge.autonomous_execution.states import StepExecutionState

app = typer.Typer(
    name="execute",
    help="Inspect and simulate the Aerion Forge execution engine.",
    no_args_is_help=True,
)

console = Console()


@app.command("create-dry-run")
def create_dry_run(
    mission_id: Annotated[
        str,
        typer.Option("--mission-id"),
    ],
    plan_id: Annotated[
        str,
        typer.Option("--plan-id"),
    ],
    step_id: Annotated[
        str,
        typer.Option("--step-id"),
    ],
    repository_root: Annotated[
        str,
        typer.Option("--repository-root"),
    ] = ".",
) -> None:
    """Create a read-only execution request."""
    request = ExecutionRequest(
        request_id=(
            f"execution-request-{mission_id}-{plan_id}-{step_id}"
        ),
        mission_id=mission_id,
        plan_id=plan_id,
        step_id=step_id,
        repository_root=repository_root,
        requested_by="cli",
        dry_run=True,
    )

    table = Table(title="Autonomous Execution Dry Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Request", request.request_id)
    table.add_row("Mission", request.mission_id)
    table.add_row("Plan", request.plan_id)
    table.add_row("Step", request.step_id)
    table.add_row("Repository", request.repository_root)
    table.add_row("Dry run", str(request.dry_run))
    console.print(table)


@app.command("report-sample")
def report_sample(
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
) -> None:
    """Render a deterministic sample execution report."""
    record = StepExecutionRecord(
        execution_id="execution-sample",
        mission_id="mission-sample",
        step_id="step-sample",
        state=StepExecutionState.SUCCEEDED,
        evidence_ids=("evidence-sample",),
        completed_at=utc_now(),
    )
    summary = execution_summary(record)

    if output is None:
        console.print_json(json.dumps(summary))
        return

    paths = write_execution_report(record, output)
    console.print(f"Reports: {paths[0]} | {paths[1]}")