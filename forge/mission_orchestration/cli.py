"""Typer commands for M3.6 Engineering Mission Orchestration."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.mission_orchestration.errors import MissionOrchestrationError
from forge.mission_orchestration.models import (
    ApprovalDecision,
    MissionApproval,
    MissionExecution,
    MissionStatus,
)
from forge.mission_orchestration.recovery import MissionRecoveryService
from forge.mission_orchestration.reporting import (
    build_mission_report,
    write_report_bundle,
)
from forge.mission_orchestration.service import MissionOrchestrationService
from forge.mission_orchestration.store import MissionCheckpointStore

mission_orchestration_app = typer.Typer(
    help="Create, inspect and execute bounded engineering missions.",
    no_args_is_help=True,
)

console = Console()


def _runtime_root() -> Path:
    root = Path.cwd().resolve()
    return root


def _checkpoint_store(root: Path) -> MissionCheckpointStore:
    return MissionCheckpointStore(
        root / "memory" / "mission_orchestration"
    )


def _execution_path(root: Path, mission_id: str) -> Path:
    return (
        root
        / "memory"
        / "mission_orchestration"
        / f"{mission_id}.execution.json"
    )


def _save_execution(root: Path, execution: MissionExecution) -> Path:
    path = _execution_path(root, execution.request.mission_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            execution.model_dump(mode="json"),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    return path


def _load_execution(root: Path, mission_id: str) -> MissionExecution:
    path = _execution_path(root, mission_id)
    return MissionExecution.model_validate_json(
        path.read_text(encoding="utf-8-sig")
    )


def _print_execution(execution: MissionExecution) -> None:
    console.print(
        f"[bold]Mission ID:[/bold] {execution.request.mission_id}"
    )
    console.print(
        f"[bold]Workflow ID:[/bold] {execution.workflow.workflow_id}"
    )
    console.print(f"[bold]Status:[/bold] {execution.status.value}")
    console.print(
        f"[bold]Current stage:[/bold] "
        f"{execution.current_stage_id or '-'}"
    )
    console.print(
        f"[bold]Stage runs:[/bold] {len(execution.stage_runs)}"
    )


@mission_orchestration_app.command("create")
def create(
    objective: Annotated[
        str,
        typer.Option("--objective", help="Mission objective."),
    ],
    path: Annotated[
        list[str],
        typer.Option(
            "--path",
            help="Repository-relative target path. Repeat as required.",
        ),
    ],
    constraint: Annotated[
        list[str] | None,
        typer.Option(
            "--constraint",
            help="Mission constraint. Repeat as required.",
        ),
    ] = None,
    outcome: Annotated[
        list[str] | None,
        typer.Option(
            "--outcome",
            help="Requested outcome. Repeat as required.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON."),
    ] = False,
) -> None:
    """Create and persist a deterministic mission."""
    root = _runtime_root()
    service = MissionOrchestrationService()

    try:
        request = service.create_request(
            repository_root=root,
            objective=objective,
            requested_paths=tuple(path),
            constraints=tuple(constraint or ()),
            requested_outcomes=tuple(outcome or ()),
        )
        execution = service.create_execution(request)
        written = _save_execution(root, execution)
    except (OSError, MissionOrchestrationError, ValueError) as exc:
        console.print(
            f"[bold red]Mission creation failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(execution.model_dump_json())
        return

    _print_execution(execution)
    console.print(f"[bold]Saved:[/bold] {written}")


@mission_orchestration_app.command("run-next")
def run_next(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission identifier."),
    ],
    approve: Annotated[
        bool,
        typer.Option(
            "--approve",
            help="Approve the current gated stage.",
        ),
    ] = False,
    approved_by: Annotated[
        str | None,
        typer.Option(
            "--approved-by",
            help="Approver identity when using --approve.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON."),
    ] = False,
) -> None:
    """Execute exactly one mission stage."""
    root = _runtime_root()
    service = MissionOrchestrationService()

    try:
        execution = _load_execution(root, mission_id)
        approval = None
        if approve:
            approval = MissionApproval(
                decision=ApprovalDecision.APPROVED,
                approved_by=approved_by or "operator",
                reason="approved from Forge CLI",
            )

        updated = service.run_next(
            execution,
            approval=approval,
        )
        checkpoint = service.checkpoint(
            updated,
            _checkpoint_store(root),
        )
        updated = updated.model_copy(
            update={"checkpoint_id": checkpoint.checkpoint_id}
        )
        _save_execution(root, updated)
    except (OSError, MissionOrchestrationError, ValueError) as exc:
        console.print(
            f"[bold red]Mission execution failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    if json_output:
        console.print_json(updated.model_dump_json())
        return

    _print_execution(updated)


@mission_orchestration_app.command("show")
def show(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission identifier."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON."),
    ] = False,
) -> None:
    """Show persisted mission execution state."""
    root = _runtime_root()

    try:
        execution = _load_execution(root, mission_id)
    except (OSError, ValueError) as exc:
        console.print(
            f"[bold red]Mission load failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=2) from exc

    if json_output:
        console.print_json(execution.model_dump_json())
        return

    _print_execution(execution)

    table = Table(title="Stage Runs")
    table.add_column("Stage")
    table.add_column("Attempt", justify="right")
    table.add_column("Status")

    for run in execution.stage_runs:
        table.add_row(
            run.stage_id,
            str(run.attempt_number),
            run.status.value,
        )

    console.print(table)


@mission_orchestration_app.command("resume")
def resume(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission identifier."),
    ],
) -> None:
    """Resume a mission from its latest checkpoint."""
    root = _runtime_root()

    try:
        execution = _load_execution(root, mission_id)
        checkpoint = _checkpoint_store(root).load(mission_id)
        resumed = MissionRecoveryService().resume(
            execution,
            checkpoint,
        )
        _save_execution(root, resumed)
    except (OSError, MissionOrchestrationError, ValueError) as exc:
        console.print(
            f"[bold red]Mission resume failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    _print_execution(resumed)


@mission_orchestration_app.command("cancel")
def cancel(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission identifier."),
    ],
    reason: Annotated[
        str,
        typer.Option("--reason", help="Cancellation reason."),
    ],
) -> None:
    """Cancel a non-terminal mission."""
    root = _runtime_root()

    try:
        execution = _load_execution(root, mission_id)
        cancelled = MissionRecoveryService().cancel(
            execution,
            reason=reason,
        )
        _save_execution(root, cancelled)
    except (OSError, MissionOrchestrationError, ValueError) as exc:
        console.print(
            f"[bold red]Mission cancellation failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    _print_execution(cancelled)


@mission_orchestration_app.command("report")
def report(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission identifier."),
    ],
    destination: Annotated[
        Path,
        typer.Option(
            "--destination",
            help="Report output directory.",
        ),
    ] = Path("reports/latest/mission_orchestration"),
) -> None:
    """Build and persist JSON and Markdown mission reports."""
    root = _runtime_root()

    try:
        execution = _load_execution(root, mission_id)
        completed_at = (
            datetime.now(UTC)
            if execution.status
            in {
                MissionStatus.COMPLETED,
                MissionStatus.CANCELLED,
                MissionStatus.FAILED,
            }
            else None
        )
        mission_report = build_mission_report(
            execution,
            started_at=execution.request.created_at,
            completed_at=completed_at,
        )
        written = write_report_bundle(
            mission_report,
            root / destination,
        )
    except (OSError, MissionOrchestrationError, ValueError) as exc:
        console.print(
            f"[bold red]Mission report failed:[/bold red] {exc}"
        )
        raise typer.Exit(code=1) from exc

    console.print(
        f"[bold]Report ID:[/bold] {mission_report.report_id}"
    )
    for name, path in written.items():
        console.print(f"- {name}: {path}")


@mission_orchestration_app.command("list")
def list_missions(
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print JSON."),
    ] = False,
) -> None:
    """List persisted mission executions."""
    root = _runtime_root()
    directory = root / "memory" / "mission_orchestration"

    mission_ids = tuple(
        sorted(
            path.name.removesuffix(".execution.json")
            for path in directory.glob("*.execution.json")
        )
    ) if directory.is_dir() else ()

    if json_output:
        console.print_json(json.dumps(list(mission_ids)))
        return

    table = Table(title="Mission Orchestration Executions")
    table.add_column("Mission ID")
    for mission_id in mission_ids:
        table.add_row(mission_id)
    console.print(table)