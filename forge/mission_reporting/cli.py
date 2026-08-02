"""Typer commands for deterministic Mission Reporting."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.engineering_memory.errors import EngineeringMemoryError
from forge.engineering_memory.models import EngineeringMemoryStore
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
from forge.mission_reporting.errors import (
    MissionReportingDisabledError,
    MissionReportingError,
    MissionReportingReportError,
    MissionReportingValidationError,
)
from forge.mission_reporting.models import (
    MissionReport,
    MissionReportingConfiguration,
)
from forge.mission_reporting.service import MissionReportingService
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

report_app = typer.Typer(
    help="Build and inspect deterministic Mission Reports.",
    no_args_is_help=True,
)
console = Console()


def _configuration() -> MissionReportingConfiguration:
    return MissionReportingConfiguration()


def _service(
    settings: Settings,
) -> MissionReportingService:
    return MissionReportingService(
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


def _engineering_memory(
    settings: Settings,
) -> EngineeringMemoryStore:
    repository = EngineeringMemoryRepository(
        settings.memory_path / EngineeringMemoryService.STORE_NAME,
    )
    return repository.load()


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
        raise MissionReportingValidationError(
            "Persisted Task generation does not match the Mission fingerprint."
        )

    source_fingerprints = dict(mission.source_fingerprints)
    source_fingerprints["mission"] = mission.mission_fingerprint
    source_fingerprints["task_set"] = generation.task_set_fingerprint

    return TaskSet(
        mission_id=mission.mission_id,
        mission_fingerprint=mission.mission_fingerprint,
        task_set_fingerprint=(generation.task_set_fingerprint),
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


def _report_path(
    settings: Settings,
) -> Path:
    return settings.reports_path / "MISSION_REPORT.json"


def _load_report(
    settings: Settings,
) -> MissionReport:
    path = _report_path(settings)

    if not path.is_file():
        raise MissionReportingReportError("No persisted Mission Report was found.")

    try:
        return MissionReport.model_validate_json(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MissionReportingReportError("Unable to read the persisted Mission Report.") from exc


def _error_exit_code(
    exc: (
        MissionReportingError
        | MissionPlanningError
        | TaskManagementError
        | ImpactDecisionError
        | EngineeringMemoryError
    ),
) -> int:
    if isinstance(
        exc,
        (
            MissionNotFoundError,
            TaskNotFoundError,
            ImpactDecisionNotFoundError,
        ),
    ):
        return 2

    if isinstance(
        exc,
        MissionReportingDisabledError,
    ):
        return 3

    if isinstance(
        exc,
        MissionReportingReportError,
    ):
        return 4

    if isinstance(
        exc,
        MissionReportingValidationError,
    ):
        return 5

    return 1


def _print_report(
    report: MissionReport,
) -> None:
    console.print(f"[bold]Report ID:[/bold] {report.report_id}")
    console.print(f"[bold]Mission ID:[/bold] {report.mission_id}")
    console.print(f"[bold]Title:[/bold] {report.title}")
    console.print(f"[bold]Status:[/bold] {report.status.value}")
    console.print(f"[bold]Tasks:[/bold] {report.statistics.task_count}")
    console.print(f"[bold]Risks:[/bold] {report.statistics.risk_count}")
    console.print(f"[bold]Traceability:[/bold] {report.statistics.traceability_count}")
    console.print(f"[bold]Fingerprint:[/bold] {report.report_fingerprint}")


def _print_sections(
    report: MissionReport,
) -> None:
    table = Table(title="Mission Report Sections")
    table.add_column("Type")
    table.add_column("Title")
    table.add_column("Sources", justify="right")
    table.add_column("Items", justify="right")

    for section in report.sections:
        table.add_row(
            section.section_type.value,
            section.title,
            str(len(section.source_ids)),
            str(len(section.content)),
        )

    console.print(table)


@report_app.command("build")
def build(
    mission_id: Annotated[
        str,
        typer.Argument(help="Persisted Mission ID to report."),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the result as deterministic JSON.",
        ),
    ] = False,
    no_reports: Annotated[
        bool,
        typer.Option(
            "--no-reports",
            help="Build without writing report files.",
        ),
    ] = False,
) -> None:
    """Build a report from persisted engineering artifacts."""

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
        engineering_memory = _engineering_memory(settings)

        result = _service(settings).build(
            mission,
            task_set,
            assessment,
            engineering_memory,
            write_reports=not no_reports,
        )
    except (
        MissionReportingError,
        MissionPlanningError,
        TaskManagementError,
        ImpactDecisionError,
        EngineeringMemoryError,
    ) as exc:
        console.print(f"[bold red]Mission Reporting failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                result.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    _print_report(result.report)

    if result.report_paths:
        console.print(f"[bold]Reports written:[/bold] {len(result.report_paths)}")


@report_app.command("show")
def show(
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete report as JSON.",
        ),
    ] = False,
    sections: Annotated[
        bool,
        typer.Option(
            "--sections",
            help="Display the report section table.",
        ),
    ] = False,
) -> None:
    """Show the latest persisted Mission Report."""

    settings = Settings()

    try:
        report = _load_report(settings)
    except MissionReportingError as exc:
        console.print(f"[bold red]Mission Report query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                report.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        return

    _print_report(report)

    if sections:
        _print_sections(report)
