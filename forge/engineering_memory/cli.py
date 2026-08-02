"""Typer commands for deterministic Engineering Memory."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.engineering_memory.errors import (
    EngineeringMemoryDisabledError,
    EngineeringMemoryError,
    EngineeringMemoryNotFoundError,
    EngineeringMemoryPersistenceError,
    EngineeringMemoryReportError,
    EngineeringMemorySchemaMismatchError,
    EngineeringMemoryStoreCorruptionError,
    EngineeringMemoryValidationError,
)
from forge.engineering_memory.models import (
    EngineeringMemoryConfiguration,
    MemoryRecord,
    MemoryType,
)
from forge.engineering_memory.query import EngineeringMemoryQuery
from forge.engineering_memory.service import EngineeringMemoryService
from forge.engineering_memory.store import EngineeringMemoryRepository
from forge.impact.errors import (
    ImpactDecisionError,
    ImpactDecisionNotFoundError,
)
from forge.impact.models import ImpactAssessment
from forge.impact.query import ImpactQuery
from forge.impact.service import ImpactDecisionService
from forge.impact.store import ImpactRepository
from forge.planning.errors import (
    MissionNotFoundError,
    MissionPlanningError,
)
from forge.planning.query import MissionPlanQuery
from forge.planning.store import MissionPlanRepository
from forge.tasks.errors import (
    TaskManagementError,
    TaskNotFoundError,
)
from forge.tasks.models import TaskSet
from forge.tasks.query import TaskQuery
from forge.tasks.store import TaskRepository

memory_app = typer.Typer(
    help="Build and inspect deterministic Engineering Memory.",
    no_args_is_help=True,
)
console = Console()


def _configuration() -> EngineeringMemoryConfiguration:
    return EngineeringMemoryConfiguration()


def _service(
    settings: Settings,
) -> EngineeringMemoryService:
    return EngineeringMemoryService(
        memory_path=settings.memory_path,
        reports_path=settings.reports_path,
        configuration=_configuration(),
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


def _impact_query(
    settings: Settings,
) -> ImpactQuery:
    repository = ImpactRepository(
        settings.memory_path / ImpactDecisionService.STORE_NAME,
    )
    return ImpactQuery(repository.load())


def _memory_query(
    settings: Settings,
) -> EngineeringMemoryQuery:
    repository = EngineeringMemoryRepository(
        settings.memory_path / EngineeringMemoryService.STORE_NAME,
        history_limit=_configuration().history_limit,
    )
    return EngineeringMemoryQuery(repository.load())


def _task_set(
    mission_id: str,
    mission_query: MissionPlanQuery,
    task_query: TaskQuery,
) -> TaskSet:
    mission = mission_query.get_mission(mission_id)
    tasks = task_query.list_tasks_for_mission(mission_id)

    if not tasks:
        raise TaskNotFoundError(f"No persisted tasks were found for mission: {mission_id}")

    generation = task_query.get_generation(mission_id)

    if generation.mission_fingerprint != mission.mission_fingerprint:
        raise EngineeringMemoryValidationError(
            "Persisted Task generation does not match the Mission fingerprint."
        )

    source_fingerprints = dict(mission.source_fingerprints)
    source_fingerprints["mission"] = mission.mission_fingerprint
    source_fingerprints["task_set"] = generation.task_set_fingerprint

    return TaskSet(
        mission_id=mission.mission_id,
        mission_fingerprint=mission.mission_fingerprint,
        task_set_fingerprint=generation.task_set_fingerprint,
        tasks=tasks,
        statistics=generation.statistics,
        source_fingerprints={key: source_fingerprints[key] for key in sorted(source_fingerprints)},
    )


def _latest_assessment(
    mission_id: str,
    query: ImpactQuery,
) -> ImpactAssessment:
    assessments = query.list_by_mission(mission_id)

    if not assessments:
        raise ImpactDecisionNotFoundError(
            f"No persisted Impact Assessment was found for mission: {mission_id}"
        )

    return assessments[-1]


def _error_exit_code(
    exc: (
        EngineeringMemoryError | MissionPlanningError | TaskManagementError | ImpactDecisionError
    ),
) -> int:
    if isinstance(
        exc,
        (
            EngineeringMemoryNotFoundError,
            MissionNotFoundError,
            TaskNotFoundError,
            ImpactDecisionNotFoundError,
        ),
    ):
        return 2

    if isinstance(exc, EngineeringMemoryDisabledError):
        return 3

    if isinstance(
        exc,
        (
            EngineeringMemoryPersistenceError,
            EngineeringMemoryStoreCorruptionError,
            EngineeringMemorySchemaMismatchError,
            EngineeringMemoryReportError,
        ),
    ):
        return 4

    if isinstance(exc, EngineeringMemoryValidationError):
        return 5

    return 1


def _print_record(
    record: MemoryRecord,
) -> None:
    console.print(f"[bold]Memory ID:[/bold] {record.memory_id}")
    console.print(f"[bold]Type:[/bold] {record.memory_type.value}")
    console.print(f"[bold]Title:[/bold] {record.title}")
    console.print(f"[bold]Summary:[/bold] {record.summary}")
    console.print(f"[bold]Confidence:[/bold] {record.confidence.value}")
    console.print(f"[bold]Retention:[/bold] {record.retention_policy.value}")
    console.print(f"[bold]Evidence:[/bold] {len(record.evidence)}")
    console.print(f"[bold]Relationships:[/bold] {len(record.relationships)}")


def _print_records(
    records: tuple[MemoryRecord, ...],
) -> None:
    table = Table(title="Engineering Memory")
    table.add_column("Memory ID")
    table.add_column("Type")
    table.add_column("Title")
    table.add_column("Missions", justify="right")
    table.add_column("Tasks", justify="right")
    table.add_column("Evidence", justify="right")

    for record in records:
        table.add_row(
            record.memory_id,
            record.memory_type.value,
            record.title,
            str(len(record.mission_ids)),
            str(len(record.task_ids)),
            str(len(record.evidence)),
        )

    console.print(table)


@memory_app.command("build")
def build(
    mission_id: Annotated[
        str,
        typer.Argument(help=("Persisted Mission ID whose Engineering Memory will be built.")),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete result as deterministic JSON.",
        ),
    ] = False,
    no_persist: Annotated[
        bool,
        typer.Option(
            "--no-persist",
            help="Build without writing the Engineering Memory store.",
        ),
    ] = False,
    no_reports: Annotated[
        bool,
        typer.Option(
            "--no-reports",
            help="Build without writing Engineering Memory reports.",
        ),
    ] = False,
) -> None:
    """Build memory from persisted Mission, Tasks, and Impact."""

    settings = Settings()

    try:
        mission_query = _mission_query(settings)
        task_query = _task_query(settings)
        impact_query = _impact_query(settings)

        mission = mission_query.get_mission(mission_id)
        task_set = _task_set(
            mission_id,
            mission_query,
            task_query,
        )
        assessment = _latest_assessment(
            mission_id,
            impact_query,
        )

        result = _service(settings).build(
            mission,
            task_set,
            assessment,
            persist=not no_persist,
            write_reports=not no_reports,
        )
    except (
        EngineeringMemoryError,
        MissionPlanningError,
        TaskManagementError,
        ImpactDecisionError,
    ) as exc:
        console.print(f"[bold red]Engineering Memory build failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_records(result.records)
    console.print(f"[bold]Generation:[/bold] {result.generation.generation_id}")

    if result.report_paths:
        console.print("\n[bold]Reports[/bold]")

        for report_path in result.report_paths:
            console.print(f"- {report_path}")


@memory_app.command("list")
def list_records(
    mission_id: Annotated[
        str | None,
        typer.Option("--mission"),
    ] = None,
    task_id: Annotated[
        str | None,
        typer.Option("--task"),
    ] = None,
    assessment_id: Annotated[
        str | None,
        typer.Option("--assessment"),
    ] = None,
    capability_id: Annotated[
        str | None,
        typer.Option("--capability"),
    ] = None,
    milestone: Annotated[
        str | None,
        typer.Option("--milestone"),
    ] = None,
    memory_type: Annotated[
        str | None,
        typer.Option("--type"),
    ] = None,
    tag: Annotated[
        str | None,
        typer.Option("--tag"),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """List persisted Engineering Memory records."""

    settings = Settings()

    try:
        query = _memory_query(settings)
        records = query.list_all()

        if mission_id is not None:
            records = tuple(
                record for record in records if mission_id.strip() in record.mission_ids
            )

        if task_id is not None:
            records = tuple(record for record in records if task_id.strip() in record.task_ids)

        if assessment_id is not None:
            records = tuple(
                record for record in records if assessment_id.strip() in record.assessment_ids
            )

        if capability_id is not None:
            records = tuple(
                record for record in records if capability_id.strip() in record.capability_ids
            )

        if milestone is not None:
            records = tuple(record for record in records if milestone.strip() in record.milestones)

        if memory_type is not None:
            try:
                selected_type = MemoryType(memory_type.strip().lower().replace("-", "_"))
            except ValueError as exc:
                console.print(f"[bold red]Invalid memory type:[/bold red] {memory_type}")
                raise typer.Exit(code=2) from exc

            records = tuple(record for record in records if record.memory_type is selected_type)

        if tag is not None:
            records = query.by_tag(tag)

            if any(
                (
                    mission_id,
                    task_id,
                    assessment_id,
                    capability_id,
                    milestone,
                    memory_type,
                )
            ):
                selected_ids = {record.memory_id for record in records}
                records = tuple(
                    record for record in query.list_all() if record.memory_id in selected_ids
                )

    except EngineeringMemoryError as exc:
        console.print(f"[bold red]Engineering Memory query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                [record.model_dump(mode="json") for record in records],
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_records(records)


@memory_app.command("show")
def show(
    memory_id: Annotated[
        str,
        typer.Argument(help="Persisted Engineering Memory ID to inspect."),
    ],
    json_output: Annotated[
        bool,
        typer.Option("--json"),
    ] = False,
) -> None:
    """Show one persisted Engineering Memory record."""

    settings = Settings()

    try:
        record = _memory_query(settings).get(memory_id)
    except EngineeringMemoryError as exc:
        console.print(f"[bold red]Engineering Memory query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                record.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_record(record)
