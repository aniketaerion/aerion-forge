"""CLI for M4.1 Frontend Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.frontend.reporting import (
    report_summary,
    write_report_bundle,
)
from forge.domain_intelligence.frontend.service import (
    FrontendIntelligenceService,
)
from forge.domain_intelligence.models import FrontendAnalysisRequest

frontend_app = typer.Typer(
    help="Analyze frontend architecture and generate reports.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> FrontendAnalysisRequest:
    return FrontendAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@frontend_app.command("analyze")
def analyze_frontend(
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
            help="Repository-relative frontend project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print complete JSON report."),
    ] = False,
) -> None:
    """Analyze a frontend project."""
    report = FrontendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = report_summary(report)

    table = Table(title="Frontend Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Frameworks",
        ", ".join(
            framework.value
            for framework in report.project.frameworks
        ),
    )
    table.add_row(
        "Package manager",
        report.project.package_manager or "unknown",
    )
    table.add_row(
        "Findings",
        str(summary["finding_count"]),
    )

    console.print(table)


@frontend_app.command("summary")
def summarize_frontend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise JSON summary."""
    report = FrontendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )
    console.print_json(
        json.dumps(
            report_summary(report),
            sort_keys=True,
        )
    )


@frontend_app.command("report")
def report_frontend(
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
    ] = Path("reports/latest/frontend"),
) -> None:
    """Generate JSON and Markdown report files."""
    root = repository_root.resolve()
    report = FrontendIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_report_bundle(
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


@frontend_app.command("validate")
def validate_frontend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that frontend analysis completes successfully."""
    report = FrontendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Frontend analysis validation passed.[/green]"
    )
    console.print(
        f"Report ID: {report.report_id}"
    )