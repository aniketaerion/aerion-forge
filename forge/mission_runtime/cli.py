"""CLI for the M5.8 Forge Mission Runtime."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer

from forge.mission_runtime.runner import (
    approve_current_boundary,
    list_sessions,
    load_session,
    run_objective,
)

app = typer.Typer(
    name="mission-runtime",
    help="Run and inspect M5.8 Forge Mission Runtime sessions.",
    no_args_is_help=True,
)


@app.callback()
def main() -> None:
    """Forge Mission Runtime command group."""


@app.command("about")
def about() -> None:
    """Describe the mission runtime integration boundary."""
    typer.echo(
        "M5.8 Forge Mission Runtime: context -> memory -> planning -> "
        "approval -> execution -> verification -> review."
    )


@app.command("run")
def run(
    objective: Annotated[
        str,
        typer.Argument(help="Engineering objective."),
    ],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root", help="Target Git repository root."),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print session JSON."),
    ] = False,
) -> None:
    """Create a mission and run it to the next control boundary."""
    result = run_objective(
        objective=objective,
        repository_root=repository_root,
    )

    if json_output:
        typer.echo(result.session.model_dump_json())
        return

    typer.echo(f"Session ID: {result.session_id}")
    typer.echo(f"Status: {result.status}")


@app.command("approve")
def approve(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    approved_by: Annotated[
        str,
        typer.Option("--approved-by"),
    ] = "operator",
    reason: Annotated[
        str,
        typer.Option("--reason"),
    ] = "approved",
) -> None:
    """Approve the current mission boundary and resume execution."""
    result = approve_current_boundary(
        session_id=session_id,
        repository_root=repository_root,
        approved_by=approved_by,
        reason=reason,
    )
    typer.echo(f"Session ID: {result.session_id}")
    typer.echo(f"Status: {result.status}")


@app.command("show")
def show(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Show one persisted mission-runtime session."""
    session = load_session(
        session_id=session_id,
        repository_root=repository_root,
    )

    if json_output:
        typer.echo(session.model_dump_json())
        return

    typer.echo(f"Session ID: {session.session_id}")
    typer.echo(f"Status: {session.status.value}")
    typer.echo(f"Objective: {session.request.objective.objective}")


@app.command("list")
def list_command(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """List persisted mission-runtime sessions."""
    session_ids = list_sessions(
        repository_root=repository_root,
    )

    if json_output:
        typer.echo(json.dumps(list(session_ids)))
        return

    for session_id in session_ids:
        typer.echo(session_id)