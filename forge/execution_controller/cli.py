"""Execution Controller command-line interface."""

import json
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.table import Table

from forge.config.settings import Settings
from forge.execution_controller.errors import (
    ExecutionControllerError,
    ExecutionReportError,
    ExecutionValidationError,
)
from forge.execution_controller.models import (
    ExecutionRequest,
    ExecutionSession,
)
from forge.execution_controller.service import (
    ExecutionControllerService,
)

execution_app = typer.Typer(
    help="Create and inspect controlled engineering execution requests.",
    no_args_is_help=True,
)
console = Console()

REQUEST_FILE = "execution-request.json"
SESSION_FILE = "execution-session.json"


def _settings() -> Settings:
    settings = Settings.from_runtime()
    settings.ensure_runtime_directories()
    return settings


def _service() -> ExecutionControllerService:
    return ExecutionControllerService()


def _request_path(settings: Settings) -> Path:
    return settings.memory_path / REQUEST_FILE


def _session_path(settings: Settings) -> Path:
    return settings.memory_path / SESSION_FILE


def _write_model(
    path: Path,
    payload: dict[str, object],
) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary = path.with_name(path.name + ".tmp")

    try:
        temporary.write_text(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n",
            encoding="utf-8",
            newline="\n",
        )
        temporary.replace(path)
    except OSError as exc:
        try:
            if temporary.exists():
                temporary.unlink()
        except OSError:
            pass

        raise ExecutionReportError(
            f"Unable to persist Execution Controller artifact: {path}"
        ) from exc


def _load_request(
    settings: Settings,
) -> ExecutionRequest:
    path = _request_path(settings)

    if not path.is_file():
        raise ExecutionValidationError("No persisted execution request was found.")

    try:
        return ExecutionRequest.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise ExecutionValidationError("Persisted execution request is invalid.") from exc


def _load_session(
    settings: Settings,
) -> ExecutionSession:
    path = _session_path(settings)

    if not path.is_file():
        raise ExecutionValidationError("No persisted execution session was found.")

    try:
        return ExecutionSession.model_validate_json(path.read_text(encoding="utf-8"))
    except (OSError, ValidationError) as exc:
        raise ExecutionValidationError("Persisted execution session is invalid.") from exc


def _exit_code(
    exc: ExecutionControllerError,
) -> int:
    if isinstance(exc, ExecutionValidationError):
        return 5

    if isinstance(exc, ExecutionReportError):
        return 4

    return 1


def _print_request(
    request: ExecutionRequest,
) -> None:
    console.print(f"[bold]Request ID:[/bold] {request.request_id}")
    console.print(f"[bold]Mission ID:[/bold] {request.mission_id}")
    console.print(f"[bold]Tasks:[/bold] {len(request.task_ids)}")
    console.print(f"[bold]Operations:[/bold] {len(request.requested_operations)}")
    console.print(f"[bold]Dry run:[/bold] {'yes' if request.dry_run else 'no'}")
    console.print(f"[bold]Fingerprint:[/bold] {request.request_fingerprint}")


def _print_session(
    session: ExecutionSession,
) -> None:
    console.print(f"[bold]Session ID:[/bold] {session.session_id}")
    console.print(f"[bold]Mission ID:[/bold] {session.request.mission_id}")
    console.print(f"[bold]State:[/bold] {session.current_state.value}")
    console.print(f"[bold]Operations:[/bold] {session.statistics.operation_count}")
    console.print(f"[bold]Transitions:[/bold] {len(session.transitions)}")
    console.print(f"[bold]Evidence:[/bold] {len(session.evidence)}")


@execution_app.command("request")
def request(
    mission_id: Annotated[
        str,
        typer.Argument(help="Mission ID for the execution request."),
    ],
    task: Annotated[
        list[str] | None,
        typer.Option(
            "--task",
            help="Task ID. Repeat for multiple tasks.",
        ),
    ] = None,
    operation: Annotated[
        list[str] | None,
        typer.Option(
            "--operation",
            help=("Requested operation type. Repeat for multiple operations."),
        ),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run/--execute",
            help=("Create a non-mutating dry-run request or an execution request."),
        ),
    ] = True,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the request as JSON.",
        ),
    ] = False,
) -> None:
    """Create and persist an execution request."""

    settings = _settings()

    try:
        execution_request = _service().create_request(
            mission_id=mission_id,
            task_ids=tuple(task or ()),
            requested_operations=tuple(operation or ()),
            dry_run=dry_run,
            source_fingerprints={},
        )

        _write_model(
            _request_path(settings),
            execution_request.model_dump(mode="json"),
        )
    except ExecutionControllerError as exc:
        console.print(f"[bold red]Execution request failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(execution_request.model_dump_json())
        return

    _print_request(execution_request)


@execution_app.command("validate")
def validate(
    known_mission_id: Annotated[
        str | None,
        typer.Option(
            "--mission",
            help=("Expected mission ID. Defaults to the persisted request mission."),
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print validation output as JSON.",
        ),
    ] = False,
) -> None:
    """Validate the latest persisted execution request."""

    settings = _settings()

    try:
        execution_request = _load_request(settings)

        result = _service().validate_request(
            execution_request,
            known_mission_id=(known_mission_id or execution_request.mission_id),
            known_task_ids=(execution_request.task_ids),
            required_source_fingerprints=dict(execution_request.source_fingerprints),
        )
    except ExecutionControllerError as exc:
        console.print(f"[bold red]Execution validation failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc

    if json_output:
        console.print_json(result.model_dump_json())
    else:
        console.print(f"[bold]Valid:[/bold] {'yes' if result.valid else 'no'}")

        if result.findings:
            table = Table(title="Execution Validation Findings")
            table.add_column("Code")
            table.add_column("Message")
            table.add_column("Severity")

            for finding in result.findings:
                table.add_row(
                    finding.code,
                    finding.message,
                    ("error" if finding.is_error else "warning"),
                )

            console.print(table)

    if not result.valid:
        raise typer.Exit(code=5)


@execution_app.command("show")
def show(
    artifact: Annotated[
        str,
        typer.Option(
            "--artifact",
            help="Artifact to show: request or session.",
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
    """Show the latest persisted execution artifact."""

    settings = _settings()
    normalized = artifact.strip().lower()

    try:
        if normalized == "request":
            execution_request = _load_request(settings)

            if json_output:
                console.print_json(execution_request.model_dump_json())
            else:
                _print_request(execution_request)

            return

        if normalized == "session":
            session = _load_session(settings)

            if json_output:
                console.print_json(session.model_dump_json())
            else:
                _print_session(session)

            return

        raise ExecutionValidationError("Artifact must be 'request' or 'session'.")

    except ExecutionControllerError as exc:
        console.print(f"[bold red]Execution query failed:[/bold red] {exc}")
        raise typer.Exit(code=_exit_code(exc)) from exc


@execution_app.command("list")
def list_artifacts(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print artifact metadata as JSON.",
        ),
    ] = False,
) -> None:
    """List persisted Execution Controller artifacts."""

    settings = _settings()

    artifacts = []

    for artifact_type, path in (
        ("request", _request_path(settings)),
        ("session", _session_path(settings)),
    ):
        if path.is_file():
            artifacts.append(
                {
                    "artifact_type": artifact_type,
                    "path": path.as_posix(),
                    "size": path.stat().st_size,
                }
            )

    if json_output:
        console.print_json(
            json.dumps(
                artifacts,
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    table = Table(title="Execution Controller Artifacts")
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
