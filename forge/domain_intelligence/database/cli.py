"""CLI for M4.3 Database Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.database.models import (
    DatabaseAnalysisRequest,
)
from forge.domain_intelligence.database.reporting import (
    database_report_summary,
    write_database_report_bundle,
)
from forge.domain_intelligence.database.service import (
    DatabaseIntelligenceService,
)

database_app = typer.Typer(
    help="Analyze database architecture and generate reports.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> DatabaseAnalysisRequest:
    return DatabaseAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@database_app.command("analyze")
def analyze_database(
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
            help="Repository-relative database project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print complete JSON report."),
    ] = False,
) -> None:
    """Analyze a database project."""
    report = DatabaseIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = database_report_summary(report)

    table = Table(title="Database Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Engines",
        ", ".join(
            engine.value for engine in report.project.engines
        ),
    )
    table.add_row("Tables", str(summary["table_count"]))
    table.add_row("Columns", str(summary["column_count"]))
    table.add_row(
        "Relationships",
        str(summary["relationship_count"]),
    )
    table.add_row("Findings", str(summary["finding_count"]))

    console.print(table)


@database_app.command("summary")
def summarize_database(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise database summary."""
    report = DatabaseIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            database_report_summary(report),
            sort_keys=True,
        )
    )


@database_app.command("report")
def report_database(
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
    ] = Path("reports/latest/database"),
) -> None:
    """Generate database JSON and Markdown reports."""
    root = repository_root.resolve()
    report = DatabaseIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_database_report_bundle(
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


@database_app.command("validate")
def validate_database(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that database analysis completes successfully."""
    report = DatabaseIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Database analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")