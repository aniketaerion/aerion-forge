"""CLI commands for autonomous planning."""

from __future__ import annotations

import json

import typer

from forge.autonomous_planning.context import PlanningContext
from forge.autonomous_planning.models import PlanningRequest
from forge.autonomous_planning.plan_generation import (
    AutonomousPlanGenerator,
)
from forge.autonomous_planning.policies import (
    AutonomousPlanningPolicy,
)
from forge.autonomous_planning.reporting import (
    PlanningReport,
    planning_report_json,
    planning_report_markdown,
)
from forge.autonomous_planning.states import PlanningIntent
from forge.autonomous_planning.validation import (
    AutonomousPlanValidator,
)

app = typer.Typer(
    help="Generate and inspect autonomous engineering plans."
)


@app.command("simulate")
def simulate_plan(
    objective: str = typer.Option(
        "Implement a repository-grounded feature",
        "--objective",
        help="Objective for the simulated plan.",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
) -> None:
    """Generate and validate a deterministic in-memory plan."""
    policy = AutonomousPlanningPolicy()
    request = PlanningRequest(
        request_id="simulation-request",
        objective=objective,
        repository_root="simulation-repository",
        intent=PlanningIntent.IMPLEMENT_FEATURE,
        acceptance_criteria=("All configured checks pass.",),
        created_by="Aerion Forge CLI",
    )
    context = PlanningContext(
        repository_root="simulation-repository",
        repository_fingerprint="simulation-fingerprint",
        known_capabilities=("analysis", "editing", "testing"),
        validation_commands=(
            "python -m ruff check .",
            "python -m mypy .",
            "python -m pytest -p no:cacheprovider",
        ),
    )
    generated = AutonomousPlanGenerator(
        policy=policy
    ).generate(
        request=request,
        context=context,
    )
    validation = AutonomousPlanValidator(
        policy=policy
    ).validate(generated.plan)
    report = PlanningReport(
        plan=generated.plan,
        validation=validation,
    )

    if output_format == "markdown":
        typer.echo(planning_report_markdown(report))
        return

    if output_format != "json":
        raise typer.BadParameter(
            "Format must be 'json' or 'markdown'."
        )

    typer.echo(planning_report_json(report))


@app.command("policy")
def show_policy() -> None:
    """Show the default autonomous-planning policy."""
    typer.echo(
        json.dumps(
            AutonomousPlanningPolicy().model_dump(
                mode="json"
            ),
            indent=2,
            sort_keys=True,
        )
    )