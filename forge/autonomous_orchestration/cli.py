"""Read-only CLI for the M5.3 autonomous mission orchestrator."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_orchestration.models import MissionSession
from forge.autonomous_orchestration.reporting import (
    orchestration_summary,
    write_orchestration_report,
)
from forge.autonomous_orchestration.states import OrchestrationState

app = typer.Typer(
    name="orchestrate",
    help="Inspect the Aerion Forge autonomous mission orchestrator.",
    no_args_is_help=True,
)

console = Console()


def sample_session() -> MissionSession:
    """Build a deterministic sample session for CLI inspection."""
    return MissionSession(
        session_id="session-sample",
        mission_id="mission-sample",
        plan_id="plan-sample",
        plan_version=1,
        repository_root=".",
        state=OrchestrationState.PAUSED,
        current_step_id="step-sample",
    )


@app.command("status-sample")
def status_sample() -> None:
    """Render deterministic sample orchestration status."""
    summary = orchestration_summary(sample_session())

    table = Table(title="Autonomous Mission Orchestration")
    table.add_column("Field")
    table.add_column("Value")

    for key in (
        "session_id",
        "mission_id",
        "plan_id",
        "plan_version",
        "state",
        "current_step_id",
        "cycle_count",
        "execution_count",
        "version",
    ):
        table.add_row(key, str(summary[key]))

    console.print(table)


@app.command("report-sample")
def report_sample(
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
) -> None:
    """Render or write a deterministic sample report."""
    session = sample_session()

    if output is None:
        console.print_json(
            json.dumps(orchestration_summary(session))
        )
        return

    paths = write_orchestration_report(session, output)
    console.print(f"Reports: {paths[0]} | {paths[1]}")