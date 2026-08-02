"""Typer commands for deterministic Safe Change Planning."""

import json
from pathlib import Path
from typing import Annotated, Literal

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.safe_change_planning.errors import (
    ChangePlanningConfigurationError,
    ChangePlanningPersistenceError,
    ChangePlanningReportError,
    ChangePlanningValidationError,
    ChangePlanNotFoundError,
    SafeChangePlanningError,
)
from forge.safe_change_planning.models import (
    ChangeRequest,
    SafeChangePlan,
)
from forge.safe_change_planning.service import (
    SAFE_CHANGE_MEMORY_FILE,
    SAFE_CHANGE_REQUEST_FILE,
    SafeChangePlanningService,
)

safe_change_app = typer.Typer(
    help="Create and inspect deterministic Safe Change Plans.",
    no_args_is_help=True,
)

console = Console()

ArtifactType = Literal["request", "plan"]


def _settings() -> Settings:
    settings = Settings.from_runtime()
    settings.ensure_runtime_directories()
    return settings


def _service() -> SafeChangePlanningService:
    return SafeChangePlanningService()


def _request_path(settings: Settings) -> Path:
    return settings.memory_path / SAFE_CHANGE_REQUEST_FILE


def _plan_path(settings: Settings) -> Path:
    return settings.memory_path / SAFE_CHANGE_MEMORY_FILE


def _exit_code(exc: SafeChangePlanningError) -> int:
    if isinstance(exc, ChangePlanNotFoundError):
        return 2

    if isinstance(exc, ChangePlanningConfigurationError):
        return 3

    if isinstance(
        exc,
        (
            ChangePlanningPersistenceError,
            ChangePlanningReportError,
        ),
    ):
        return 4

    if isinstance(exc, ChangePlanningValidationError):
        return 5

    return 1


def _load_request(settings: Settings) -> ChangeRequest:
    return _service().load_request(settings.memory_path)


def _load_plan(settings: Settings) -> SafeChangePlan:
    return _service().load_plan(settings.memory_path)


def _print_request(request: ChangeRequest) -> None:
    console.print(f"[bold]Request ID:[/bold] {request.request_id}")
    console.print(f"[bold]Mission ID:[/bold] {request.mission_id}")
    console.print(f"[bold]Tasks:[/bold] {len(request.task_ids)}")
    console.print(f"[bold]Objective:[/bold] {request.objective}")
    console.print(f"[bold]Fingerprint:[/bold] {request.request_fingerprint}")


def _print_plan(plan: SafeChangePlan) -> None:
    console.print(f"[bold]Plan ID:[/bold] {plan.plan_id}")
    console.print(f"[bold]Mission ID:[/bold] {plan.request.mission_id}")
    console.print(f"[bold]Risk:[/bold] {plan.risk_assessment.risk_level.value}")
    console.print(f"[bold]Targets:[/bold] {plan.statistics.target_count}")
    console.print(f"[bold]Actions:[/bold] {plan.statistics.action_count}")
    console.print(
        "[bold]Approval required:[/bold] "
        f"{'yes' if plan.risk_assessment.approval_required else 'no'}"
    )


@safe_change_app.command("request")
def request(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission ID for the Safe Change request."),
    ],
    objective: Annotated[
        str,
        typer.Option(
            "--objective",
            help="Required change objective.",
        ),
    ],
    task: Annotated[
        list[str] | None,
        typer.Option(
            "--task",
            help="Task ID. Repeat for multiple tasks.",
        ),
    ] = None,
    constraint: Annotated[
        list[str] | None,
        typer.Option(
            "--constraint",
            help="Planning constraint. Repeat as needed.",
        ),
    ] = None,
    outcome: Annotated[
        list[str] | None,
        typer.Option(
            "--outcome",
            help="Requested outcome. Repeat as needed.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the request as JSON.",
        ),
    ] = False,
) -> None:
    """Create and persist a deterministic change request."""

    settings = _settings()

    try:
        change_request = _service().create_request(
            mission_id=mission_id,
            task_ids=tuple(task or ()),
            objective=objective,
            constraints=tuple(constraint or ()),
            requested_outcomes=tuple(outcome or ()),
            source_fingerprints={},
        )

        _service().save_request(
            change_request,
            settings.memory_path,
        )
    except SafeChangePlanningError as exc:
        console.print(f"[bold red]Safe Change request failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(change_request.model_dump_json())
        return

    _print_request(change_request)


@safe_change_app.command("validate")
def validate(
    known_mission_id: Annotated[
        str | None,
        typer.Option(
            "--mission",
            help="Expected mission ID.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print validation as JSON.",
        ),
    ] = False,
) -> None:
    """Validate the persisted Safe Change request."""

    settings = _settings()

    try:
        change_request = _load_request(settings)

        result = _service().validate_request(
            change_request,
            known_mission_id=(known_mission_id or change_request.mission_id),
            known_task_ids=change_request.task_ids,
            required_source_fingerprints=dict(change_request.source_fingerprints),
        )
    except SafeChangePlanningError as exc:
        console.print(f"[bold red]Safe Change validation failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        console.print(f"[bold]Valid:[/bold] {'yes' if result.valid else 'no'}")

        if result.findings:
            table = Table(title="Safe Change Validation Findings")
            table.add_column("Code")
            table.add_column("Message")
            table.add_column("Severity")

            for finding in result.findings:
                table.add_row(
                    finding.code,
                    finding.message,
                    finding.severity.value,
                )

            console.print(table)

    if not result.valid:
        raise typer.Exit(code=5)


@safe_change_app.command("show")
def show(
    artifact: Annotated[
        ArtifactType,
        typer.Argument(
            help="Artifact to show: request or plan.",
        ),
    ] = "request",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the artifact as JSON.",
        ),
    ] = False,
) -> None:
    """Show the persisted request or plan."""

    settings = _settings()

    try:
        model: ChangeRequest | SafeChangePlan = (
            _load_request(settings) if artifact == "request" else _load_plan(settings)
        )
    except SafeChangePlanningError as exc:
        console.print(f"[bold red]Safe Change artifact failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(model.model_dump_json())
        return

    if isinstance(model, ChangeRequest):
        _print_request(model)
    else:
        _print_plan(model)


@safe_change_app.command("render")
def render(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print written report names as JSON.",
        ),
    ] = False,
) -> None:
    """Render reports for the persisted Safe Change Plan."""

    settings = _settings()

    try:
        plan = _load_plan(settings)
        written = _service().write_reports(
            plan,
            settings.reports_path,
        )
    except SafeChangePlanningError as exc:
        console.print(f"[bold red]Safe Change rendering failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                {
                    "plan_id": plan.plan_id,
                    "reports": list(written),
                },
                sort_keys=True,
            )
        )
        return

    console.print(f"[bold]Plan ID:[/bold] {plan.plan_id}")
    console.print(f"[bold]Reports written:[/bold] {len(written)}")

    for name in written:
        console.print(f"- {name}")


@safe_change_app.command("list")
def list_artifacts(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print artifact inventory as JSON.",
        ),
    ] = False,
) -> None:
    """List persisted Safe Change Planning artifacts."""

    settings = _settings()

    candidates = (
        ("request", _request_path(settings)),
        ("plan", _plan_path(settings)),
    )

    artifacts = [
        {
            "artifact_type": artifact_type,
            "path": str(path),
            "size": path.stat().st_size,
        }
        for artifact_type, path in candidates
        if path.is_file()
    ]

    if json_output:
        console.print_json(
            json.dumps(
                artifacts,
                sort_keys=True,
            )
        )
        return

    table = Table(title="Safe Change Planning Artifacts")
    table.add_column("Type")
    table.add_column("Path")
    table.add_column("Bytes", justify="right")

    for artifact in artifacts:
        table.add_row(
            str(artifact["artifact_type"]),
            str(artifact["path"]),
            str(artifact["size"]),
        )

    console.print(table)
