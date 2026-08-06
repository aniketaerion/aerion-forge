"""CLI for M4.6 Embedded Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.embedded.models import (
    EmbeddedAnalysisRequest,
)
from forge.domain_intelligence.embedded.reporting import (
    embedded_report_summary,
    write_embedded_report_bundle,
)
from forge.domain_intelligence.embedded.service import (
    EmbeddedIntelligenceService,
)

embedded_app = typer.Typer(
    help=(
        "Analyze PX4, ArduPilot, ROS 2, STM32, embedded interfaces, "
        "messages, build systems, and safety findings."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> EmbeddedAnalysisRequest:
    return EmbeddedAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@embedded_app.command("analyze")
def analyze_embedded(
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            help="Git repository root.",
        ),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option(
            "--project-root",
            help="Repository-relative embedded project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete JSON report.",
        ),
    ] = False,
) -> None:
    """Analyze an embedded software project."""
    report = EmbeddedIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = embedded_report_summary(report)

    table = Table(title="Embedded Domain Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Platforms",
        ", ".join(summary["platforms"]) or "none detected",
    )
    table.add_row("Components", str(summary["component_count"]))
    table.add_row("Interfaces", str(summary["interface_count"]))
    table.add_row("Messages", str(summary["message_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    table.add_row("Build files", str(summary["build_file_count"]))

    console.print(table)


@embedded_app.command("summary")
def summarize_embedded(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise embedded-analysis summary."""
    report = EmbeddedIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            embedded_report_summary(report),
            sort_keys=True,
        )
    )


@embedded_app.command("report")
def report_embedded(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Repository-relative report destination.",
        ),
    ] = Path("reports/latest/embedded"),
) -> None:
    """Generate embedded JSON and Markdown reports."""
    root = repository_root.resolve()
    report = EmbeddedIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_embedded_report_bundle(
        report,
        root / destination,
    )

    console.print_json(
        json.dumps(
            {
                name: str(path)
                for name, path in sorted(written.items())
            },
            sort_keys=True,
        )
    )


@embedded_app.command("validate")
def validate_embedded(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that embedded analysis completes."""
    report = EmbeddedIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Embedded-domain analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")