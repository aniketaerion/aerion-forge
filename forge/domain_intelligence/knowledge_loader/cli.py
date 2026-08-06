"""CLI for M4.7 Knowledge Loader Intelligence."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadRequest,
)
from forge.domain_intelligence.knowledge_loader.reporting import (
    knowledge_loader_report_summary,
    write_knowledge_loader_report_bundle,
)
from forge.domain_intelligence.knowledge_loader.service import (
    KnowledgeLoaderService,
)

knowledge_loader_app = typer.Typer(
    help=(
        "Discover, load, normalize, chunk, validate, cache, "
        "version, and report repository knowledge."
    ),
    no_args_is_help=True,
)

console = Console()


def _request(
    repository_root: Path,
    project_root: str,
    chunk_size: int,
) -> KnowledgeLoadRequest:
    return KnowledgeLoadRequest(
        repository_root=str(repository_root.resolve()),
        project_root=project_root,
        chunk_size=chunk_size,
    )


@knowledge_loader_app.command("load")
def load_knowledge(
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
            help="Repository-relative knowledge root.",
        ),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option(
            "--chunk-size",
            min=128,
            max=50000,
            help="Maximum characters per chunk.",
        ),
    ] = 4000,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete JSON report.",
        ),
    ] = False,
) -> None:
    """Load and analyze repository knowledge."""
    report = KnowledgeLoaderService().load(
        _request(
            repository_root,
            project_root,
            chunk_size,
        )
    )

    if json_output:
        console.print_json(report.model_dump_json())
        return

    summary = knowledge_loader_report_summary(report)

    table = Table(title="Knowledge Loader Intelligence")
    table.add_column("Field")
    table.add_column("Value")

    table.add_row("Project root", str(summary["project_root"]))
    table.add_row("Sources", str(summary["source_count"]))
    table.add_row("Documents", str(summary["document_count"]))
    table.add_row("Chunks", str(summary["chunk_count"]))
    table.add_row("Findings", str(summary["finding_count"]))
    table.add_row(
        "Source bytes",
        str(summary["total_source_bytes"]),
    )
    table.add_row(
        "Estimated tokens",
        str(summary["total_chunk_tokens"]),
    )

    console.print(table)


@knowledge_loader_app.command("summary")
def summarize_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", min=128, max=50000),
    ] = 4000,
) -> None:
    """Print a concise knowledge-loader summary."""
    report = KnowledgeLoaderService().load(
        _request(
            repository_root,
            project_root,
            chunk_size,
        )
    )

    console.print_json(
        json.dumps(
            knowledge_loader_report_summary(report),
            sort_keys=True,
        )
    )


@knowledge_loader_app.command("report")
def report_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", min=128, max=50000),
    ] = 4000,
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Repository-relative report destination.",
        ),
    ] = Path("reports/latest/knowledge-loader"),
) -> None:
    """Generate knowledge-loader JSON and Markdown reports."""
    root = repository_root.resolve()
    report = KnowledgeLoaderService().load(
        _request(
            root,
            project_root,
            chunk_size,
        )
    )
    written = write_knowledge_loader_report_bundle(
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


@knowledge_loader_app.command("validate")
def validate_knowledge(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    project_root: Annotated[
        str,
        typer.Option("--project-root"),
    ] = ".",
    chunk_size: Annotated[
        int,
        typer.Option("--chunk-size", min=128, max=50000),
    ] = 4000,
) -> None:
    """Validate that knowledge loading completes."""
    report = KnowledgeLoaderService().load(
        _request(
            repository_root,
            project_root,
            chunk_size,
        )
    )

    console.print(
        "[green]Knowledge-loader validation passed.[/green]"
    )
    console.print(f"Report ID: {report.report_id}")