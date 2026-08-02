"""Typer commands for deterministic Impact Decision analysis."""

import json
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.impact.errors import (
    ImpactDecisionDisabledError,
    ImpactDecisionError,
    ImpactDecisionNotFoundError,
    ImpactPersistenceError,
    ImpactReportError,
    ImpactSchemaMismatchError,
    ImpactStoreCorruptionError,
    ImpactValidationError,
)
from forge.impact.models import (
    DecisionStatus,
    ImpactAssessment,
    ImpactDecisionConfiguration,
    ImpactSeverity,
)
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

impact_app = typer.Typer(
    help="Assess and inspect deterministic engineering impacts.",
    no_args_is_help=True,
)
console = Console()


def _configuration() -> ImpactDecisionConfiguration:
    """Return the current M2.3 configuration.

    Configuration catalogue integration is intentionally deferred to the
    final Milestone 2.3 integration batch.
    """

    return ImpactDecisionConfiguration()


def _service(
    settings: Settings,
) -> ImpactDecisionService:
    return ImpactDecisionService(
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
        history_limit=_configuration().history_limit,
    )
    return ImpactQuery(repository.load())


def _task_set(
    mission_id: str,
    mission_query: MissionPlanQuery,
    task_query: TaskQuery,
) -> TaskSet:
    """Reconstruct the persisted TaskSet without decomposing the mission."""

    mission = mission_query.get_mission(mission_id)
    tasks = task_query.list_tasks_for_mission(mission_id)

    if not tasks:
        raise TaskNotFoundError(f"No persisted tasks were found for mission: {mission_id}")

    generation = task_query.get_generation(mission_id)

    if generation.mission_fingerprint != mission.mission_fingerprint:
        raise ImpactValidationError(
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


def _error_exit_code(
    exc: ImpactDecisionError | MissionPlanningError | TaskManagementError,
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

    if isinstance(exc, ImpactDecisionDisabledError):
        return 3

    if isinstance(
        exc,
        (
            ImpactPersistenceError,
            ImpactStoreCorruptionError,
            ImpactSchemaMismatchError,
            ImpactReportError,
        ),
    ):
        return 4

    if isinstance(exc, ImpactValidationError):
        return 5

    return 1


def _print_assessment(
    assessment: ImpactAssessment,
) -> None:
    console.print(f"[bold]Assessment ID:[/bold] {assessment.assessment_id}")
    console.print(f"[bold]Mission ID:[/bold] {assessment.mission_id}")
    console.print(f"[bold]Status:[/bold] {assessment.status.value.upper()}")
    console.print(f"[bold]Severity:[/bold] {assessment.overall_severity.value.upper()}")
    console.print(f"[bold]Confidence:[/bold] {assessment.confidence.value.upper()}")
    console.print(f"[bold]Selected option:[/bold] {assessment.recommendation.selected_option_id}")

    if assessment.blocking_reason is not None:
        console.print(f"[bold]Blocking reason:[/bold] {assessment.blocking_reason}")

    console.print("\n[bold]Findings[/bold]")

    for finding in assessment.findings:
        console.print(f"- {finding.finding_id}: {finding.summary} [{finding.severity.value}]")

    if assessment.recommendation.approval_requirements:
        console.print("\n[bold]Required approvals[/bold]")

        for approval_requirement in assessment.recommendation.approval_requirements:
            console.print(f"- {approval_requirement.level.value}: {approval_requirement.reason}")

    console.print("\n[bold]Validation requirements[/bold]")

    for validation_requirement in assessment.recommendation.validation_requirements:
        console.print(
            f"- {validation_requirement.category.value}: {validation_requirement.description}"
        )


def _print_assessments(
    assessments: tuple[ImpactAssessment, ...],
) -> None:
    table = Table(title="Impact Assessments")
    table.add_column("Assessment ID")
    table.add_column("Mission ID")
    table.add_column("Status")
    table.add_column("Severity")
    table.add_column("Findings", justify="right")
    table.add_column("Selected Option")

    for assessment in assessments:
        table.add_row(
            assessment.assessment_id,
            assessment.mission_id,
            assessment.status.value,
            assessment.overall_severity.value,
            str(len(assessment.findings)),
            assessment.recommendation.selected_option_id,
        )

    console.print(table)


@impact_app.command("assess")
def assess(
    mission_id: Annotated[
        str,
        typer.Argument(help="Persisted mission ID whose tasks will be assessed."),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the complete Impact Decision result as JSON.",
        ),
    ] = False,
    no_persist: Annotated[
        bool,
        typer.Option(
            "--no-persist",
            help="Build without writing the Impact Decision store.",
        ),
    ] = False,
    no_reports: Annotated[
        bool,
        typer.Option(
            "--no-reports",
            help="Build without writing Impact Decision reports.",
        ),
    ] = False,
) -> None:
    """Assess an existing persisted Mission and Task Set."""

    settings = Settings()

    try:
        mission_query = _mission_query(settings)
        task_query = _task_query(settings)
        mission = mission_query.get_mission(mission_id)
        task_set = _task_set(
            mission_id,
            mission_query,
            task_query,
        )
        result = _service(settings).assess(
            mission,
            task_set,
            persist=not no_persist,
            write_reports=not no_reports,
        )
    except (
        ImpactDecisionError,
        MissionPlanningError,
        TaskManagementError,
    ) as exc:
        console.print(f"[bold red]Impact assessment failed:[/bold red] {exc}")
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

    _print_assessment(result.assessment)
    console.print(f"[bold]Finding count:[/bold] {len(result.assessment.findings)}")

    if result.report_paths:
        console.print("\n[bold]Reports[/bold]")

        for report_path in result.report_paths:
            console.print(f"- {report_path}")


@impact_app.command("list")
def list_assessments(
    mission_id: Annotated[
        str | None,
        typer.Option(
            "--mission",
            help="Restrict results to one Mission ID.",
        ),
    ] = None,
    status: Annotated[
        str | None,
        typer.Option(
            "--status",
            help="Restrict results to one decision status.",
        ),
    ] = None,
    severity: Annotated[
        str | None,
        typer.Option(
            "--severity",
            help="Restrict results to one impact severity.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print assessments as deterministic JSON.",
        ),
    ] = False,
) -> None:
    """List persisted Impact Decision assessments."""

    settings = Settings()

    try:
        query = _impact_query(settings)
        assessments = query.list_assessments()

        if mission_id is not None:
            assessments = tuple(
                assessment for assessment in assessments if assessment.mission_id == mission_id
            )

        if status is not None:
            try:
                selected_status = DecisionStatus(status.strip().lower().replace("-", "_"))
            except ValueError as exc:
                console.print(f"[bold red]Invalid impact status:[/bold red] {status}")
                raise typer.Exit(code=2) from exc

            assessments = tuple(
                assessment for assessment in assessments if assessment.status is selected_status
            )

        if severity is not None:
            try:
                selected_severity = ImpactSeverity(severity.strip().lower().replace("-", "_"))
            except ValueError as exc:
                console.print(f"[bold red]Invalid impact severity:[/bold red] {severity}")
                raise typer.Exit(code=2) from exc

            assessments = tuple(
                assessment
                for assessment in assessments
                if (assessment.overall_severity is selected_severity)
            )

    except ImpactDecisionError as exc:
        console.print(f"[bold red]Impact query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                [assessment.model_dump(mode="json") for assessment in assessments],
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_assessments(assessments)


@impact_app.command("show")
def show(
    assessment_id: Annotated[
        str,
        typer.Argument(help="Persisted Impact Assessment ID to inspect."),
    ],
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print the assessment as deterministic JSON.",
        ),
    ] = False,
) -> None:
    """Show one persisted Impact Decision assessment."""

    settings = Settings()

    try:
        assessment = _impact_query(settings).get_assessment(assessment_id)
    except ImpactDecisionError as exc:
        console.print(f"[bold red]Impact query failed:[/bold red] {exc}")
        raise typer.Exit(code=_error_exit_code(exc)) from exc

    if json_output:
        console.print_json(
            json.dumps(
                assessment.model_dump(mode="json"),
                ensure_ascii=False,
                sort_keys=True,
                default=str,
            )
        )
        return

    _print_assessment(assessment)
