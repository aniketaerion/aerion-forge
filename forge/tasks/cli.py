"""Typer commands for deterministic Task Management."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.planning.errors import (
    MissionNotFoundError,
    MissionPersistenceError,
    MissionPlanningError,
)
from forge.planning.query import MissionPlanQuery
from forge.planning.store import MissionPlanRepository
from forge.tasks.errors import (
    TaskDefinitionError,
    TaskManagementDisabledError,
    TaskManagementError,
    TaskNotFoundError,
    TaskPersistenceError,
    TaskReportError,
    TaskSchemaMismatchError,
    TaskStoreCorruptionError,
    TaskValidationError,
)
from forge.tasks.models import (
    EngineeringTask,
    TaskManagementConfiguration,
)
from forge.tasks.query import TaskQuery
from forge.tasks.service import TaskManagementService
from forge.tasks.store import TaskRepository

task_app = typer.Typer(
    help="Build and inspect deterministic engineering tasks.",
    no_args_is_help=True,
)

console = Console()


def _configuration(
    settings: Settings,
) -> TaskManagementConfiguration:
    return TaskManagementConfiguration(
        enabled=settings.task_management_enabled,
        strict=settings.task_management_strict,
        history_limit=settings.task_management_history_limit,
        max_tasks_per_mission=(settings.task_management_max_tasks_per_mission),
        max_dependencies_per_task=(settings.task_management_max_dependencies_per_task),
        max_acceptance_criteria_per_task=(
            settings.task_management_max_acceptance_criteria_per_task
        ),
        max_validation_requirements_per_task=(
            settings.task_management_max_validation_requirements_per_task
        ),
        require_approved_mission=(settings.task_management_require_approved_mission),
        allow_blocked_tasks=(settings.task_management_allow_blocked_tasks),
    )


def _service(
    settings: Settings,
) -> TaskManagementService:
    return TaskManagementService(
        memory_path=settings.memory_path,
        reports_path=settings.reports_path,
        configuration=_configuration(settings),
    )


def _mission_query(
    settings: Settings,
) -> MissionPlanQuery:
    repository = MissionPlanRepository(
        settings.memory_path / "missions.json",
        history_limit=settings.planning_history_limit,
    )
    return MissionPlanQuery(repository.load())


def _task_query(
    settings: Settings,
) -> TaskQuery:
    repository = TaskRepository(
        settings.memory_path / "tasks.json",
        history_limit=settings.task_management_history_limit,
    )
    return TaskQuery(repository.load())


def _error_exit_code(
    exc: TaskManagementError | MissionPlanningError,
) -> int:
    if isinstance(
        exc,
        MissionNotFoundError | TaskNotFoundError | TaskDefinitionError,
    ):
        return 2

    if isinstance(exc, TaskManagementDisabledError):
        return 6

    if isinstance(exc, TaskValidationError):
        return 9

    if isinstance(exc, TaskPersistenceError):
        return 10

    if isinstance(exc, TaskReportError):
        return 11

    if isinstance(exc, TaskStoreCorruptionError):
        return 12

    if isinstance(exc, TaskSchemaMismatchError):
        return 13

    if isinstance(exc, MissionPersistenceError):
        return 7

    return 8


def _print_task(task: EngineeringTask) -> None:
    console.print(f"[bold]Task ID:[/bold] {task.task_id}")
    console.print(f"[bold]Mission ID:[/bold] {task.mission_id}")
    console.print(f"[bold]Workstream:[/bold] {task.workstream_id}")
    console.print(f"[bold]Title:[/bold] {task.title}")
    console.print(f"[bold]Status:[/bold] {task.status.value.upper()}")
    console.print(f"[bold]Priority:[/bold] {task.priority.value.upper()}")
    console.print(f"[bold]Risk:[/bold] {task.risk_level.value.upper()}")
    console.print(f"[bold]Parent:[/bold] {task.parent_task_id or 'none'}")
    console.print(f"[bold]Description:[/bold] {task.description}")


def _print_tasks(
    tasks: tuple[EngineeringTask, ...],
) -> None:
    table = Table(title="Engineering Tasks")
    table.add_column("Sequence", justify="right")
    table.add_column("Task ID")
    table.add_column("Title")
    table.add_column("Status")
    table.add_column("Priority")
    table.add_column("Risk")

    for task in tasks:
        table.add_row(
            str(task.sequence),
            task.task_id,
            task.title,
            task.status.value,
            task.priority.value,
            task.risk_level.value,
        )

    console.print(table)


@task_app.command("build")
def build(
    mission_id: Annotated[
        str,
        typer.Argument(help="Persisted mission ID to decompose into tasks."),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete Task Management result as JSON.",
        ),
    ] = False,
    no_persist: Annotated[
        bool,
        typer.Option(
            "--no-persist",
            help="Build without writing task persistence or reports.",
        ),
    ] = False,
) -> None:
    """Build deterministic tasks from a persisted Mission Plan."""

    settings = Settings()

    try:
        mission = _mission_query(settings).get_mission(mission_id)
        result = _service(settings).build(
            mission,
            persist=not no_persist,
            write_reports=not no_persist,
        )
    except (
        TaskManagementError,
        MissionPlanningError,
    ) as exc:
        console.print(f"[bold red]Task build failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                result.model_dump(mode="json"),
                sort_keys=True,
                default=str,
            )
        )
        return

    console.print(f"[bold]Mission ID:[/bold] {result.generation.mission_id}")
    console.print(f"[bold]Generation:[/bold] {result.generation.generation_id}")
    console.print(f"[bold]Tasks:[/bold] {result.generation.task_count}")
    console.print(f"[bold]Reports:[/bold] {len(result.report_paths)}")


@task_app.command("list")
def list_tasks(
    mission_id: Annotated[
        str | None,
        typer.Option(
            "--mission",
            help="Restrict results to one mission ID.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print tasks as JSON.",
        ),
    ] = False,
) -> None:
    """List persisted engineering tasks."""

    settings = Settings()

    try:
        query = _task_query(settings)
        tasks = (
            query.list_tasks_for_mission(mission_id)
            if mission_id is not None
            else query.list_tasks()
        )
    except TaskManagementError as exc:
        console.print(f"[bold red]Task query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                [task.model_dump(mode="json") for task in tasks],
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_tasks(tasks)


@task_app.command("show")
def show(
    task_id: Annotated[
        str,
        typer.Argument(help="Persisted task ID to inspect."),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the task as JSON.",
        ),
    ] = False,
) -> None:
    """Show one persisted engineering task."""

    settings = Settings()

    try:
        task = _task_query(settings).get_task(task_id)
    except TaskManagementError as exc:
        console.print(f"[bold red]Task query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                task.model_dump(mode="json"),
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_task(task)
