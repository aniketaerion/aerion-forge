"""CLI for M4.5 Business Domain Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.business_domain.models import (
    BusinessDomainAnalysisRequest,
)
from forge.domain_intelligence.business_domain.reporting import (
    business_domain_report_summary,
    write_business_domain_report_bundle,
)
from forge.domain_intelligence.business_domain.service import (
    BusinessDomainIntelligenceService,
)

business_domain_app = typer.Typer(
    help=(
        "Analyze ERP, CRM, entities, workflows, rules, "
        "and business-domain architecture."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
) -> BusinessDomainAnalysisRequest:
    return BusinessDomainAnalysisRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
    )


@business_domain_app.command("analyze")
def analyze_business_domain(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root", help="Git repository root."),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option(
            "--project-root",
            help="Repository-relative business project root.",
        ),
    ] = ".",
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the complete JSON report."),
    ] = False,
) -> None:
    """Analyze business-domain architecture."""
    report = BusinessDomainIntelligenceService().analyze(
        _request(repository_root, project_root)
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = business_domain_report_summary(report)
    table = Table(title="Business Domain Intelligence")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Project", str(summary["project_root"]))
    table.add_row(
        "Domains",
        ", ".join(
            domain.value for domain in report.project.domains
        ),
    )
    table.add_row(
        "Modules",
        ", ".join(report.project.modules) or "none detected",
    )
    table.add_row("Entities", str(summary["entity_count"]))
    table.add_row("Workflows", str(summary["workflow_count"]))
    table.add_row("Rules", str(summary["rule_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    console.print(table)


@business_domain_app.command("summary")
def summarize_business_domain(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Print a concise business-domain summary."""
    report = BusinessDomainIntelligenceService().analyze(
        _request(repository_root, project_root)
    )
    console.print_json(
        json.dumps(
            business_domain_report_summary(report),
            sort_keys=True,
        )
    )


@business_domain_app.command("report")
def report_business_domain(
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
    ] = Path("reports/latest/business-domain"),
) -> None:
    """Generate business-domain JSON and Markdown reports."""
    root = repository_root.resolve()
    report = BusinessDomainIntelligenceService().analyze(
        _request(root, project_root)
    )
    written = write_business_domain_report_bundle(
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


@business_domain_app.command("validate")
def validate_business_domain(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
) -> None:
    """Validate that business-domain analysis completes."""
    report = BusinessDomainIntelligenceService().analyze(
        _request(repository_root, project_root)
    )
    console.print(
        "[green]Business-domain analysis validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")