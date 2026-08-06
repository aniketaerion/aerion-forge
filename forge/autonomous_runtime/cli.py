"""Read-only CLI for the M5.1 autonomous runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_runtime.identifiers import (
    mission_identifier,
    mission_request_identifier,
)
from forge.autonomous_runtime.lifecycle import transition_mission
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.reporting import (
    mission_summary,
    write_mission_report,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    MissionState,
)

app = typer.Typer(
    name="autonomous",
    help="Inspect and simulate the Aerion Forge autonomous runtime.",
    no_args_is_help=True,
)

console = Console()


def _dry_run_mission(
    objective: str,
    repository_root: str,
) -> AutonomousMission:
    request_payload = {
        "objective": objective,
        "repository_root": repository_root,
        "requested_by": "cli",
    }
    request = MissionRequest(
        request_id=mission_request_identifier(request_payload),
        objective=objective,
        repository_root=repository_root,
        requested_authority=AuthorityLevel.A1_PLAN,
        requested_by="cli",
    )
    return AutonomousMission(
        mission_id=mission_identifier(
            {
                "request_id": request.request_id,
                "objective": objective,
            }
        ),
        request=request,
    )


@app.command("create-dry-run")
def create_dry_run(
    objective: Annotated[
        str,
        typer.Option(
            "--objective",
            help="Bounded engineering objective.",
        ),
    ],
    repository_root: Annotated[
        str,
        typer.Option(
            "--repository-root",
            help="Repository root used for the mission contract.",
        ),
    ] = ".",
    output: Annotated[
        Path | None,
        typer.Option(
            "--output",
            help="Optional report directory.",
        ),
    ] = None,
) -> None:
    """Create an in-memory read-only mission contract."""
    mission = _dry_run_mission(
        objective,
        repository_root,
    )
    summary = mission_summary(mission)

    table = Table(title="Autonomous Mission Dry Run")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Mission", str(summary["mission_id"]))
    table.add_row("State", str(summary["state"]))
    table.add_row("Authority", str(summary["granted_authority"]))
    table.add_row(
        "Transitions",
        ", ".join(summary["available_transitions"]),
    )
    console.print(table)

    if output is not None:
        paths = write_mission_report(mission, output)
        console.print(f"Reports: {paths[0]} | {paths[1]}")


@app.command("simulate-transition")
def simulate_transition(
    target: Annotated[
        MissionState,
        typer.Option(
            "--target",
            case_sensitive=False,
        ),
    ],
    objective: Annotated[
        str,
        typer.Option("--objective"),
    ] = "Simulate autonomous mission lifecycle.",
    repository_root: Annotated[
        str,
        typer.Option("--repository-root"),
    ] = ".",
) -> None:
    """Simulate one legal transition without repository mutation."""
    mission = _dry_run_mission(
        objective,
        repository_root,
    )
    updated = transition_mission(mission, target)

    console.print_json(
        json.dumps(mission_summary(updated))
    )