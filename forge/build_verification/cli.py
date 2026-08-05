"""Typer commands for M3.7 Build Verification."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.build_verification.errors import BuildVerificationError
from forge.build_verification.models import VerificationTool
from forge.build_verification.service import BuildVerificationService
from forge.build_verification.store import BuildVerificationStore

build_verification_app = typer.Typer(
    help="Run bounded build verification and produce release-gate evidence.",
    no_args_is_help=True,
)

console = Console()


def _parse_tools(values: list[str]) -> tuple[VerificationTool, ...]:
    try:
        return tuple(VerificationTool(value) for value in values)
    except ValueError as exc:
        raise typer.BadParameter(
            f"unsupported verification tool: {exc}"
        ) from exc


@build_verification_app.command("run")
def run_verification(
    objective: Annotated[
        str,
        typer.Option("--objective", help="Verification objective."),
    ],
    tool: Annotated[
        list[str],
        typer.Option(
            "--tool",
            help="Verification tool. Repeat as required.",
        ),
    ],
    path: Annotated[
        list[str] | None,
        typer.Option(
            "--path",
            help="Repository-relative target path. Repeat as required.",
        ),
    ] = None,
    report_directory: Annotated[
        Path,
        typer.Option(
            "--report-directory",
            help="Directory for JSON and Markdown reports.",
        ),
    ] = Path("reports/latest/build_verification"),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the release decision as JSON."),
    ] = False,
) -> None:
    """Create and execute one bounded verification request."""
    root = Path.cwd().resolve()
    service = BuildVerificationService()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )

    try:
        request = service.create_request(
            root,
            objective=objective,
            tools=_parse_tools(tool),
            target_paths=tuple(path or ()),
        )
        decision = service.verify(
            request,
            store=store,
            report_directory=root / report_directory,
        )
    except (BuildVerificationError, OSError, ValueError) as exc:
        console.print(
            f"[bold red]Build verification failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(decision.model_dump_json())
        return

    console.print(
        f"[bold]Decision:[/bold] {decision.decision.value}"
    )
    console.print(
        f"[bold]Decision ID:[/bold] {decision.decision_id}"
    )
    console.print(
        f"[bold]Evidence ID:[/bold] {decision.evidence_id}"
    )

    for reason in decision.reasons:
        console.print(f"- {reason}")


@build_verification_app.command("show-evidence")
def show_evidence(
    evidence_id: Annotated[
        str,
        typer.Argument(help="Verification evidence identifier."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print evidence as JSON."),
    ] = False,
) -> None:
    """Show persisted verification evidence."""
    root = Path.cwd().resolve()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )

    try:
        evidence = store.load_evidence(evidence_id)
    except (BuildVerificationError, OSError, ValueError) as exc:
        console.print(
            f"[bold red]Evidence load failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=2) from exc

    if json_output:
        console.print_json(evidence.model_dump_json())
        return

    console.print(f"[bold]Evidence ID:[/bold] {evidence.evidence_id}")
    console.print(f"[bold]Status:[/bold] {evidence.status.value}")
    console.print(
        f"[bold]Revision:[/bold] {evidence.request.source_revision}"
    )
    console.print(
        f"[bold]Fingerprint:[/bold] {evidence.repository_fingerprint}"
    )

    table = Table(title="Verification Steps")
    table.add_column("Step")
    table.add_column("Status")
    table.add_column("Exit Code")
    table.add_column("Duration")

    for result in evidence.step_results:
        table.add_row(
            result.step_id,
            result.status.value,
            "-" if result.exit_code is None else str(result.exit_code),
            f"{result.duration_seconds:.3f}s",
        )

    console.print(table)


@build_verification_app.command("show-decision")
def show_decision(
    decision_id: Annotated[
        str,
        typer.Argument(help="Release decision identifier."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print decision as JSON."),
    ] = False,
) -> None:
    """Show one persisted release-gate decision."""
    root = Path.cwd().resolve()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )

    try:
        decision = store.load_decision(decision_id)
    except (BuildVerificationError, OSError, ValueError) as exc:
        console.print(
            f"[bold red]Decision load failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=2) from exc

    if json_output:
        console.print_json(decision.model_dump_json())
        return

    console.print(
        f"[bold]Decision:[/bold] {decision.decision.value}"
    )
    console.print(
        f"[bold]Decision ID:[/bold] {decision.decision_id}"
    )
    console.print(
        f"[bold]Evidence ID:[/bold] {decision.evidence_id}"
    )

    for reason in decision.reasons:
        console.print(f"- {reason}")


@build_verification_app.command("list")
def list_evidence(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print evidence IDs as JSON."),
    ] = False,
) -> None:
    """List persisted verification evidence."""
    root = Path.cwd().resolve()
    store = BuildVerificationStore(
        root / "memory" / "build_verification"
    )
    evidence_ids = store.list_evidence_ids()

    if json_output:
        console.print_json(json.dumps(list(evidence_ids)))
        return

    table = Table(title="Build Verification Evidence")
    table.add_column("Evidence ID")

    for evidence_id in evidence_ids:
        table.add_row(evidence_id)

    console.print(table)