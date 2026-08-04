"""Typer commands for Safe Code Editing v1."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.safe_code_editing.errors import SafeCodeEditingError
from forge.safe_code_editing.service import SafeCodeEditingService

edit_app = typer.Typer(
    help="Dry-run or apply deterministic Safe Code Editing requests.",
    no_args_is_help=True,
)

console = Console()


def _service() -> SafeCodeEditingService:
    return SafeCodeEditingService()


def _exit_code(exc: SafeCodeEditingError) -> int:
    name = type(exc).__name__
    if "Approval" in name:
        return 3
    if "Path" in name or "Binary" in name or "Encoding" in name:
        return 4
    if "Fingerprint" in name or "ExpectedText" in name or "Overlapping" in name:
        return 5
    if "Write" in name or "Rollback" in name:
        return 6
    return 1


@edit_app.command("run")
def run(
    request_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="SafeEditRequest JSON file.",
        ),
    ],
    apply: Annotated[
        bool,
        typer.Option(
            "--apply",
            help="Apply the transaction. Without this flag, execution is a dry run.",
        ),
    ] = False,
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Explicitly approve apply mode.",
        ),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the structured report as JSON.",
        ),
    ] = False,
    report: Annotated[
        Path | None,
        typer.Option(
            "--report",
            help="Optional JSON report destination.",
        ),
    ] = None,
) -> None:
    """Execute one bounded Safe Edit request."""
    try:
        result = _service().execute_file(
            request_file,
            apply=apply,
            approved=approve,
        )
        if report is not None:
            _service().write_report(result, report)
    except SafeCodeEditingError as exc:
        console.print(f"[bold red]Safe Code Editing failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(result.model_dump_json())
        return

    console.print(f"[bold]Request ID:[/bold] {result.request_id}")
    console.print(f"[bold]Transaction ID:[/bold] {result.transaction_id}")
    console.print(f"[bold]Mode:[/bold] {'apply' if result.approved else 'dry-run'}")

    table = Table(title="Safe Code Editing Results")
    table.add_column("Path")
    table.add_column("Changed")
    table.add_column("Result fingerprint")
    for file_result in result.file_results:
        table.add_row(
            file_result.relative_path,
            "yes" if file_result.changed else "no",
            file_result.resulting_fingerprint,
        )
    console.print(table)

    for file_result in result.file_results:
        if file_result.unified_diff:
            console.print(file_result.unified_diff)