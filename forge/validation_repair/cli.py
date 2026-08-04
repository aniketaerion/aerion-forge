"""Typer commands for M3.4 Validation and Repair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.validation_repair.errors import ValidationRepairError
from forge.validation_repair.models import ValidationCommand, ValidationTool
from forge.validation_repair.service import ValidationRepairService

repair_app = typer.Typer(
    help="Run validation and prepare bounded repair sessions.",
    no_args_is_help=True,
)

console = Console()


def _commands(timeout: int) -> tuple[ValidationCommand, ...]:
    return (
        ValidationCommand(
            command_id="ruff",
            tool=ValidationTool.RUFF,
            arguments=(".",),
            timeout_seconds=timeout,
        ),
        ValidationCommand(
            command_id="mypy",
            tool=ValidationTool.MYPY,
            arguments=(".",),
            timeout_seconds=timeout,
        ),
        ValidationCommand(
            command_id="pytest",
            tool=ValidationTool.PYTEST,
            arguments=("-p", "no:cacheprovider"),
            timeout_seconds=timeout,
        ),
    )


@repair_app.command("validate")
def validate(
    repository: Annotated[Path, typer.Option("--repository")] = Path("."),
    timeout: Annotated[int, typer.Option("--timeout", min=1)] = 300,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run Ruff, MyPy and Pytest through the bounded runner."""
    service = ValidationRepairService()
    try:
        runs = service.validate(repository, _commands(timeout))
    except ValidationRepairError as exc:
        console.print(f"[bold red]Validation failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(
            json.dumps([run.model_dump(mode="json") for run in runs], sort_keys=True)
        )
        return

    table = Table(title="Validation Results")
    table.add_column("Tool")
    table.add_column("Status")
    table.add_column("Exit")
    table.add_column("Findings")
    for run in runs:
        table.add_row(
            run.command.tool.value,
            run.status.value,
            str(run.exit_code),
            str(len(run.findings)),
        )
    console.print(table)


@repair_app.command("plan")
def plan(
    repository: Annotated[Path, typer.Option("--repository")] = Path("."),
    timeout: Annotated[int, typer.Option("--timeout", min=1)] = 300,
    json_output: Annotated[bool, typer.Option("--json")] = False,
) -> None:
    """Run validation and create bounded repair candidates."""
    service = ValidationRepairService()
    try:
        runs = service.validate(repository, _commands(timeout))
        candidates = service.plan(runs)
        session = service.create_session(repository, candidates)
        report = service.build_report(session, runs)
    except ValidationRepairError as exc:
        console.print(f"[bold red]Repair planning failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {report.session_id}")
    console.print(f"[bold]Candidates:[/bold] {len(report.attempts)}")
    console.print(f"[bold]Validation clean:[/bold] {'yes' if report.succeeded else 'no'}")