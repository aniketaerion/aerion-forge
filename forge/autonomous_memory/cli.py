"""CLI commands for autonomous memory inspection."""

from __future__ import annotations

import json

import typer

from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.memory_service import (
    AutonomousMemoryService,
)
from forge.autonomous_memory.models import (
    MemoryObservation,
    MemoryQuery,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.reporting import (
    MemoryReport,
    memory_report_json,
    memory_report_markdown,
)
from forge.autonomous_memory.states import MemorySourceKind
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)

app = typer.Typer(
    help="Inspect and simulate autonomous memory behaviour."
)


def _sample_service() -> AutonomousMemoryService:
    service = AutonomousMemoryService(
        policy=AutonomousMemoryPolicy(),
        storage=InMemoryMemoryStorage(),
        index=MemoryIndex(),
    )
    service.ingest(
        MemoryObservation(
            observation_id="sample-observation-1",
            source_kind=MemorySourceKind.REPOSITORY,
            source_reference="forge/sample.py",
            repository_root="sample-repository",
            repository_fingerprint="sample-fingerprint",
            content="Repository uses Python.",
            evidence_references=("sample-evidence-1",),
            tags=("sample", "python"),
        ),
        actor="Aerion Forge",
    )
    return service


@app.command("simulate")
def simulate_memory(
    query_text: str = typer.Option(
        "python repository",
        "--query",
        help="Text used for read-only memory retrieval.",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
) -> None:
    """Run an in-memory read-only retrieval simulation."""
    service = _sample_service()
    result = service.retrieve(
        query=MemoryQuery(
            query_id="sample-query-1",
            repository_scope="sample-repository",
            requested_by="cli",
        ),
        query_text=query_text,
    )

    report = MemoryReport(
        records=result.records,
        matches=result.matches,
        learning=service.storage.all_learning(),
    )

    if output_format == "markdown":
        typer.echo(memory_report_markdown(report))
        return

    if output_format != "json":
        raise typer.BadParameter(
            "Format must be 'json' or 'markdown'."
        )

    typer.echo(memory_report_json(report))


@app.command("policy")
def show_policy() -> None:
    """Show the default-safe autonomous-memory policy."""
    payload = AutonomousMemoryPolicy().model_dump(
        mode="json"
    )
    typer.echo(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )