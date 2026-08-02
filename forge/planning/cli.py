"""Typer commands for deterministic mission planning."""

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.config import Settings
from forge.planning.errors import (
    MissionContextError,
    MissionPersistenceError,
    MissionPlanningDisabledError,
    MissionPlanningError,
    MissionReportError,
    MissionRequestError,
    MissionSchemaMismatchError,
    MissionStoreCorruptionError,
    MissionTargetNotFoundError,
    MissionValidationError,
)
from forge.planning.models import (
    MissionPlan,
    MissionPlanningConfiguration,
    MissionPlanningStatus,
)
from forge.planning.service import MissionPlanningService

mission_app = typer.Typer(
    help="Create reviewable engineering mission plans.",
    no_args_is_help=True,
)

console = Console()


def _service(settings: Settings) -> MissionPlanningService:
    configuration = MissionPlanningConfiguration(
        enabled=settings.planning_enabled,
        strict=settings.planning_strict,
        history_limit=settings.planning_history_limit,
        max_affected_areas=settings.planning_max_affected_areas,
        max_workstreams=settings.planning_max_workstreams,
        max_assumptions=settings.planning_max_assumptions,
        max_questions=settings.planning_max_questions,
        require_current_graph=settings.planning_require_current_graph,
        allow_degraded_runtime=settings.planning_allow_degraded_runtime,
    )

    return MissionPlanningService(
        memory_path=settings.memory_path,
        reports_path=settings.reports_path,
        configuration=configuration,
    )


def _error_exit_code(exc: MissionPlanningError) -> int:
    if isinstance(
        exc,
        (
            MissionRequestError,
            MissionTargetNotFoundError,
        ),
    ):
        return 2

    if isinstance(exc, MissionPlanningDisabledError):
        return 6

    if isinstance(exc, MissionContextError):
        return 7

    if isinstance(exc, MissionValidationError):
        return 9

    if isinstance(exc, MissionPersistenceError):
        return 10

    if isinstance(exc, MissionReportError):
        return 11

    if isinstance(exc, MissionStoreCorruptionError):
        return 12

    if isinstance(exc, MissionSchemaMismatchError):
        return 13

    return 8


def _status_exit_code(status: MissionPlanningStatus) -> int:
    if status is MissionPlanningStatus.READY:
        return 0

    if status is MissionPlanningStatus.READY_WITH_CONDITIONS:
        return 3

    if status is MissionPlanningStatus.BLOCKED:
        return 4

    if status is MissionPlanningStatus.INVALID:
        return 5

    return 0


def _print_default(plan: MissionPlan) -> None:
    console.print(f"[bold]Mission ID:[/bold] {plan.mission_id}")
    console.print(f"[bold]Target:[/bold] {plan.target_name}")
    console.print(
        "[bold]Status:[/bold] "
        f"{plan.status.value.replace('_', ' ').upper()}"
    )
    console.print(
        "[bold]Planning Confidence:[/bold] "
        f"{plan.planning_confidence.value.upper()}"
    )
    console.print(
        f"[bold]Risk:[/bold] {plan.risk_level.value.upper()}"
    )
    console.print(
        f"[bold]Objective:[/bold] {plan.objective.statement}"
    )

    console.print(
        "[bold]Affected Areas:[/bold] "
        f"{len(plan.affected_areas)}"
    )
    console.print(
        "[bold]Workstreams:[/bold] "
        f"{len(plan.workstreams)}"
    )

    blocking = tuple(
        item
        for item in plan.prerequisites
        if item.blocking
        and item.status.value != "satisfied"
    )

    console.print(
        "[bold]Blocking Prerequisites:[/bold] "
        f"{len(blocking)}"
    )
    console.print(
        "[bold]Required Approvals:[/bold] "
        f"{len(plan.approvals)}"
    )
    console.print(
        "[bold]Unresolved Questions:[/bold] "
        f"{len(plan.questions)}"
    )


def _print_summary(plan: MissionPlan) -> None:
    console.print(f"[bold]Mission:[/bold] {plan.mission_id}")
    console.print(f"[bold]Target:[/bold] {plan.target_name}")
    console.print(
        f"[bold]Status:[/bold] {plan.status.value}"
    )
    console.print(
        "[bold]Confidence:[/bold] "
        f"{plan.planning_confidence.value}"
    )
    console.print(
        f"[bold]Risk:[/bold] {plan.risk_level.value}"
    )
    console.print(
        f"[bold]Objective:[/bold] {plan.objective.statement}"
    )

    for item in plan.scope:
        console.print(
            f"- [{item.scope_type.value}] {item.statement}",
            markup=False,
        )


def _print_context(plan: MissionPlan) -> None:
    table = Table(title="Mission Context")
    table.add_column("Type")
    table.add_column("Name")
    table.add_column("Confidence")
    table.add_column("Evidence")

    for item in plan.context:
        table.add_row(
            item.entity_type,
            item.canonical_name,
            item.confidence.value,
            item.evidence,
        )

    console.print(table)


def _print_risks(plan: MissionPlan) -> None:
    risk_table = Table(title="Mission Risks")
    risk_table.add_column("Level")
    risk_table.add_column("Risk")
    risk_table.add_column("Mitigation")

    for risk_item in plan.risks:
        risk_table.add_row(
            risk_item.level.value,
            risk_item.statement,
            risk_item.mitigation,
        )

    console.print(risk_table)

    approval_table = Table(title="Required Approvals")
    approval_table.add_column("Approval")
    approval_table.add_column("Reason")

    for approval_item in plan.approvals:
        approval_table.add_row(
            approval_item.level.value,
            approval_item.reason,
        )

    console.print(approval_table)


def _print_assumptions(plan: MissionPlan) -> None:
    table = Table(title="Mission Assumptions")
    table.add_column("Assumption")
    table.add_column("Basis")
    table.add_column("Confirmation")

    for item in plan.assumptions:
        table.add_row(
            item.statement,
            item.basis,
            "required" if item.requires_confirmation else "not required",
        )

    console.print(table)


def _print_questions(plan: MissionPlan) -> None:
    table = Table(title="Unresolved Questions")
    table.add_column("Question")
    table.add_column("Blocking")

    for item in plan.questions:
        table.add_row(
            item.question,
            "yes" if item.blocking else "no",
        )

    console.print(table)


@mission_app.command("plan")
def plan(
    request: Annotated[
        str,
        typer.Argument(
            help="Engineering request to convert into a mission plan."
        ),
    ],
    target: Annotated[
        str | None,
        typer.Option(
            "--target",
            help="Workspace name, workspace ID, or repository path.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print the full plan as JSON."),
    ] = False,
    summary: Annotated[
        bool,
        typer.Option("--summary", help="Print a concise plan summary."),
    ] = False,
    context: Annotated[
        bool,
        typer.Option("--context", help="Print relevant project context."),
    ] = False,
    risks: Annotated[
        bool,
        typer.Option("--risks", help="Print risks and approvals."),
    ] = False,
    assumptions: Annotated[
        bool,
        typer.Option("--assumptions", help="Print assumptions."),
    ] = False,
    questions: Annotated[
        bool,
        typer.Option("--questions", help="Print unresolved questions."),
    ] = False,
    strict: Annotated[
        bool,
        typer.Option("--strict", help="Apply strict readiness rules."),
    ] = False,
    no_persist: Annotated[
        bool,
        typer.Option(
            "--no-persist",
            help="Generate without writing persistence or reports.",
        ),
    ] = False,
) -> None:
    """Create a deterministic mission-level engineering plan."""

    settings = Settings()

    try:
        result = _service(settings).plan(
            raw_request=request,
            target=target,
            strict=strict,
            persist=not no_persist,
            cwd=Path.cwd(),
        )
    except MissionPlanningError as exc:
        console.print(
            f"[bold red]Mission planning failed:[/bold red] {exc}"
        )
        raise typer.Exit(
            code=_error_exit_code(exc)
        ) from exc

    plan_value = result.plan

    if json_output:
        console.print_json(
            json.dumps(
                result.model_dump(mode="json"),
                sort_keys=True,
                default=str,
            )
        )
    elif summary:
        _print_summary(plan_value)
    elif context:
        _print_context(plan_value)
    elif risks:
        _print_risks(plan_value)
    elif assumptions:
        _print_assumptions(plan_value)
    elif questions:
        _print_questions(plan_value)
    else:
        _print_default(plan_value)

    exit_code = _status_exit_code(plan_value.status)

    if exit_code:
        raise typer.Exit(code=exit_code)


