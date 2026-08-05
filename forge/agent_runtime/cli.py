"""CLI for M3.8 Unified Agent Runtime."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.agent_runtime.adapters.base import succeeded_result
from forge.agent_runtime.adapters.planning import PlanningAdapter
from forge.agent_runtime.models import (
    AgentApproval,
    AgentCapability,
    AgentObjective,
    AgentRuntimePolicy,
    AgentSession,
    AgentStage,
    AgentStageResult,
    ApprovalKind,
)
from forge.agent_runtime.registry import AgentCapabilityRegistry
from forge.agent_runtime.reporting import write_report_bundle
from forge.agent_runtime.service import AgentRuntimeService
from forge.agent_runtime.store import AgentRuntimeStore

agent_app = typer.Typer(
    help="Run bounded unified engineering-agent sessions.",
    no_args_is_help=True,
)

console = Console()


def _planning_executor(
    repository_root: Path,
    session: AgentSession,
    stage: AgentStage,
    context: Mapping[str, object],
) -> AgentStageResult:
    del repository_root, session, context
    return succeeded_result(stage, "mission plan created")


def _service() -> AgentRuntimeService:
    registry = AgentCapabilityRegistry(
        (PlanningAdapter(_planning_executor),)
    )
    policy = AgentRuntimePolicy(
        allowed_capabilities=(
            AgentCapability.MISSION_PLANNING,
        )
    )
    return AgentRuntimeService(registry, policy)


def _store(root: Path) -> AgentRuntimeStore:
    return AgentRuntimeStore(
        root / "memory" / "agent_runtime"
    )


@agent_app.command("create")
def create_session(
    objective: Annotated[
        str,
        typer.Option("--objective", help="Engineering objective."),
    ],
    repository_root: Annotated[
        Path,
        typer.Option(
            "--repository-root",
            help="Target Git repository root.",
        ),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print session JSON."),
    ] = False,
) -> None:
    """Create and persist a planning-only agent session."""
    service = _service()
    root = repository_root.resolve()
    request = service.create_request(
        AgentObjective(
            objective=objective,
            repository_root=str(root),
            requested_capabilities=(
                AgentCapability.MISSION_PLANNING,
            ),
        )
    )
    session = service.create_session(request)
    _store(root).save_session(session)

    if json_output:
        console.print_json(session.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {session.session_id}")
    console.print(f"[bold]Status:[/bold] {session.status.value}")


@agent_app.command("approve")
def approve_session(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    approved_by: Annotated[
        str,
        typer.Option("--approved-by"),
    ] = "operator",
    reason: Annotated[
        str,
        typer.Option("--reason"),
    ] = "approved",
) -> None:
    """Add plan approval to a persisted session."""
    root = repository_root.resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)
    approval = AgentApproval(
        approval_id=f"{session_id}-plan-approval",
        kind=ApprovalKind.PLAN,
        approved=True,
        approved_by=approved_by,
        reason=reason,
    )
    updated = service.add_approval(session, approval)
    store.save_session(updated)
    console.print("[green]Approval recorded.[/green]")


@agent_app.command("run-next")
def run_next(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
) -> None:
    """Execute exactly one stage and persist the result."""
    root = repository_root.resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)
    updated = service.run_next(session)
    store.save_session(updated)
    console.print(f"[bold]Status:[/bold] {updated.status.value}")


@agent_app.command("run")
def run_to_boundary(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
) -> None:
    """Run until approval, completion, cancellation, or failure."""
    root = repository_root.resolve()
    store = _store(root)
    service = _service()
    session = store.load_session(session_id)
    updated = service.run_to_boundary(session)
    store.save_session(updated)
    console.print(f"[bold]Status:[/bold] {updated.status.value}")


@agent_app.command("show")
def show_session(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Show persisted agent-session state."""
    session = _store(repository_root.resolve()).load_session(
        session_id
    )

    if json_output:
        console.print_json(session.model_dump_json())
        return

    console.print(f"[bold]Session ID:[/bold] {session.session_id}")
    console.print(f"[bold]Status:[/bold] {session.status.value}")
    console.print(
        f"[bold]Objective:[/bold] "
        f"{session.request.objective.objective}"
    )


@agent_app.command("list")
def list_sessions(
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
) -> None:
    """List persisted agent sessions."""
    table = Table(title="Unified Agent Sessions")
    table.add_column("Session ID")

    for session_id in _store(
        repository_root.resolve()
    ).list_session_ids():
        table.add_row(session_id)

    console.print(table)


@agent_app.command("report")
def report_session(
    session_id: Annotated[str, typer.Argument()],
    repository_root: Annotated[
        Path,
        typer.Option("--repository-root"),
    ] = Path("."),
    destination: Annotated[
        Path,
        typer.Option("--destination"),
    ] = Path("reports/latest/agent_runtime"),
) -> None:
    """Write JSON and Markdown session reports."""
    root = repository_root.resolve()
    session = _store(root).load_session(session_id)
    written = write_report_bundle(
        session,
        root / destination,
    )
    console.print_json(
        json.dumps(
            {
                name: str(path)
                for name, path in written.items()
            }
        )
    )