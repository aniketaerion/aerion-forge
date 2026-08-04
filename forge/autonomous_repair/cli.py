"""Typer commands for M3.5 Autonomous Repair."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_repair.errors import AutonomousRepairError
from forge.autonomous_repair.models import (
    RepairApproval,
    RepairInput,
)
from forge.autonomous_repair.registry import RepairProviderRegistry
from forge.autonomous_repair.service import AutonomousRepairService

autonomous_repair_app = typer.Typer(
    help="Propose, dry-run and apply bounded autonomous repairs.",
    no_args_is_help=True,
)

console = Console()


def _service() -> AutonomousRepairService:
    return AutonomousRepairService()


def _load_input(path: Path) -> RepairInput:
    return _service().load_input(path)


@autonomous_repair_app.command("providers")
def providers(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print provider names as JSON."),
    ] = False,
) -> None:
    """List registered autonomous-repair providers."""
    provider_types = RepairProviderRegistry.with_builtins().list_provider_types()

    if json_output:
        console.print_json(
            json.dumps([provider.value for provider in provider_types])
        )
        return

    table = Table(title="Autonomous Repair Providers")
    table.add_column("Provider")
    for provider in provider_types:
        table.add_row(provider.value)
    console.print(table)


@autonomous_repair_app.command("propose")
def propose(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
            help="RepairInput JSON file.",
        ),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print proposal as JSON."),
    ] = False,
) -> None:
    """Generate a bounded repair proposal without modifying the repository."""
    try:
        repair_input = _load_input(input_file)
        proposal = _service().propose(repair_input)
    except AutonomousRepairError as exc:
        console.print(f"[bold red]Autonomous repair proposal failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(proposal.model_dump_json())
        return

    console.print(f"[bold]Proposal ID:[/bold] {proposal.proposal_id}")
    console.print(f"[bold]Provider:[/bold] {proposal.provider.value}")
    console.print(f"[bold]Affected files:[/bold] {len(proposal.affected_paths)}")
    for path in proposal.affected_paths:
        console.print(f"- {path}")


@autonomous_repair_app.command("dry-run")
def dry_run(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    report_directory: Annotated[
        Path | None,
        typer.Option("--report-directory"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Dry-run one bounded repair without mutating repository files."""
    try:
        service = _service()
        repair_input = service.load_input(input_file)
        proposal = service.propose(repair_input)
        request = service.build_request(
            proposal,
            repository_root=Path(repair_input.repository_root),
            dry_run=True,
        )
        report = service.execute(request)
        if report_directory is not None:
            service.write_reports(report, report_directory)
    except AutonomousRepairError as exc:
        console.print(f"[bold red]Autonomous repair dry-run failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {report.session_id}")
    console.print(f"[bold]Status:[/bold] {report.status.value}")
    console.print("[bold]Repository modified:[/bold] no")


@autonomous_repair_app.command("apply")
def apply(
    input_file: Annotated[
        Path,
        typer.Argument(
            exists=True,
            dir_okay=False,
            readable=True,
            resolve_path=True,
        ),
    ],
    approve: Annotated[
        bool,
        typer.Option("--approve", help="Explicitly approve repository mutation."),
    ] = False,
    approved_by: Annotated[
        str | None,
        typer.Option("--approved-by"),
    ] = None,
    reason: Annotated[
        str | None,
        typer.Option("--reason"),
    ] = None,
    report_directory: Annotated[
        Path | None,
        typer.Option("--report-directory"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Apply one explicitly approved bounded repair."""
    if not approve:
        console.print("[bold red]Apply requires --approve.[/bold red]")
        raise typer.Exit(code=3)

    try:
        service = _service()
        repair_input = service.load_input(input_file)
        proposal = service.propose(repair_input)
        request = service.build_request(
            proposal,
            repository_root=Path(repair_input.repository_root),
            dry_run=False,
            approval=RepairApproval(
                approved=True,
                approved_by=approved_by or "cli-user",
                reason=reason or "explicit CLI approval",
            ),
        )
        report = service.execute(
            request,
            validate=lambda _root, _proposal: True,
        )
        if report_directory is not None:
            service.write_reports(report, report_directory)
    except AutonomousRepairError as exc:
        console.print(f"[bold red]Autonomous repair apply failed:[/bold red] {exc}")
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(report.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {report.session_id}")
    console.print(f"[bold]Status:[/bold] {report.status.value}")
    console.print(f"[bold]Succeeded:[/bold] {'yes' if report.succeeded else 'no'}")