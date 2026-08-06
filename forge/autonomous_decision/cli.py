"""Read-only CLI for the M5.4 autonomous decision engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from forge.autonomous_decision.decision_journal import (
    InMemoryDecisionJournal,
)
from forge.autonomous_decision.decision_service import (
    AutonomousDecisionService,
    DecisionResult,
)
from forge.autonomous_decision.models import (
    DecisionContext,
    DecisionRequest,
)
from forge.autonomous_decision.policies import (
    AutonomousDecisionPolicy,
)
from forge.autonomous_decision.replay_guard import (
    DecisionReplayGuard,
)
from forge.autonomous_decision.reporting import (
    decision_summary,
    write_decision_report,
)

app = typer.Typer(
    name="decide",
    help="Inspect and simulate the Aerion Forge decision engine.",
    no_args_is_help=True,
)

console = Console()


def sample_decision_result(
    *,
    with_evidence: bool = True,
) -> DecisionResult:
    """Build a deterministic read-only sample decision."""
    evidence = (
        ("evidence-1", "evidence-2", "evidence-3")
        if with_evidence
        else ()
    )

    request = DecisionRequest(
        request_id="decision-request-sample",
        mission_id="mission-sample",
        session_id="session-sample",
        plan_id="plan-sample",
        plan_version=1,
        repository_root=".",
        requested_by="Aerion",
        dry_run=True,
    )
    context = DecisionContext(
        context_id="decision-context-sample",
        mission_id="mission-sample",
        session_id="session-sample",
        mission_state="executing",
        orchestration_state="step_selecting",
        current_step_id="step-sample",
        authority_level="a2_modify",
        approval_state="approved",
        repository_fingerprint="repository-fingerprint-sample",
        evidence_references=evidence,
        policy_version="1.0",
    )
    service = AutonomousDecisionService(
        policy=AutonomousDecisionPolicy(),
        journal=InMemoryDecisionJournal(),
        replay_guard=DecisionReplayGuard(),
    )

    return service.decide(request, context)


@app.command("simulate")
def simulate(
    no_evidence: Annotated[
        bool,
        typer.Option("--no-evidence"),
    ] = False,
) -> None:
    """Run a deterministic, non-mutating decision simulation."""
    result = sample_decision_result(
        with_evidence=not no_evidence
    )
    summary = decision_summary(result)

    table = Table(title="Autonomous Decision Simulation")
    table.add_column("Field")
    table.add_column("Value")

    for key in (
        "decision_id",
        "decision_kind",
        "disposition",
        "selected_candidate_id",
        "approval_required",
        "confidence",
    ):
        table.add_row(key, str(summary[key]))

    console.print(table)


@app.command("report-sample")
def report_sample(
    output: Annotated[
        Path | None,
        typer.Option("--output"),
    ] = None,
    no_evidence: Annotated[
        bool,
        typer.Option("--no-evidence"),
    ] = False,
) -> None:
    """Render or write a deterministic sample decision report."""
    result = sample_decision_result(
        with_evidence=not no_evidence
    )

    if output is None:
        console.print_json(
            json.dumps(decision_summary(result))
        )
        return

    json_path, markdown_path = write_decision_report(
        result,
        output,
    )
    console.print(
        f"Reports: {json_path} | {markdown_path}"
    )