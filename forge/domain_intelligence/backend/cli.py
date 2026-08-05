"""CLI for M4.2 Backend Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
)
from forge.domain_intelligence.backend.reporting import (
    backend_report_summary,
    write_backend_report_bundle,
)
from forge.domain_intelligence.backend.service import (
    BackendIntelligenceService,
)

backend_app = typer.Typer(
    help="Analyze backend architecture and generate reports.",
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> BackendAnalysisRequest:
    return BackendAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@backend_app.command("analyze")
def analyze_backend(
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
            help="Repository-relative backend project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print complete JSON report."),
    ] = False,
) -> None:
    """Analyze a backend project."""
    report = BackendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = backend_report_summary(report)

    table = Table(title="Backend Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Runtimes",
        ", ".join(
            runtime.value
            for runtime in report.project.runtimes
        ),
    )
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


@backend_app.command("summary")
def summarize_backend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise backend summary."""
    report = BackendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print_json(
        json.dumps(
            backend_report_summary(report),
            sort_keys=True,
        )
    )


@backend_app.command("report")
def report_backend(
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
    ] = Path("reports/latest/backend"),
) -> None:
    """Generate backend JSON and Markdown reports."""
    root = repository_root.resolve()
    report = BackendIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_backend_report_bundle(
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


@backend_app.command("validate")
def validate_backend(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that backend analysis completes successfully."""
    report = BackendIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    console.print(
        "[green]Backend analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")