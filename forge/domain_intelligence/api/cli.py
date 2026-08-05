"""CLI for M4.4 API Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.api.models import (
    ApiAnalysisRequest,
)
from forge.domain_intelligence.api.reporting import (
    api_report_summary,
    write_api_report_bundle,
)
from forge.domain_intelligence.api.service import (
    ApiIntelligenceService,
)

api_app = typer.Typer(
    help="Analyze API architecture, contracts, compatibility, and security.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> ApiAnalysisRequest:
    return ApiAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@api_app.command("analyze")
def analyze_api(
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
            help="Repository-relative API project root.",
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
    """Analyze an API project."""
    report = ApiIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = api_report_summary(report)

    table = Table(title="API Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Styles",
        ", ".join(
            style.value for style in report.project.styles
        ),
    )
    table.add_row("Contracts", str(summary["contract_count"]))
    table.add_row("Endpoints", str(summary["endpoint_count"]))
    table.add_row(
        "Authenticated endpoints",
        str(summary["authenticated_endpoint_count"]),
    )
    table.add_row("Findings", str(summary["finding_count"]))

    console.print(table)


@api_app.command("summary")
def summarize_api(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise API summary."""
    report = ApiIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            api_report_summary(report),
            sort_keys=True,
        )
    )


@api_app.command("report")
def report_api(
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
    ] = Path("reports/latest/api"),
) -> None:
    """Generate API JSON and Markdown reports."""
    root = repository_root.resolve()
    report = ApiIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_api_report_bundle(
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


@api_app.command("validate")
def validate_api(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that API analysis completes successfully."""
    report = ApiIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]API analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")