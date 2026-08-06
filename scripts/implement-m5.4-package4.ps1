[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent

    New-Item `
        -ItemType Directory `
        -Path $Directory `
        -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

$ExpectedBranch = "feature/m5.4-autonomous-decision-engine"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.4 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_decision\reporting.py" @'
"""Reporting helpers for autonomous decisions."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from forge.autonomous_decision.decision_service import DecisionResult


def decision_summary(
    result: DecisionResult,
) -> dict[str, Any]:
    """Return a deterministic JSON-serializable decision summary."""
    record = result.record

    return {
        "decision_id": record.decision_id,
        "request_id": record.request_id,
        "context_id": record.context_id,
        "decision_kind": record.decision_kind.value,
        "disposition": record.disposition.value,
        "selected_candidate_id": record.selected_candidate_id,
        "alternative_candidate_ids": list(
            record.alternative_candidate_ids
        ),
        "rejected_candidate_ids": list(
            record.rejected_candidate_ids
        ),
        "assessment_ids": list(record.assessment_ids),
        "evidence_references": list(
            record.evidence_references
        ),
        "approval_required": record.approval_required,
        "confidence": record.confidence,
        "context_fingerprint": record.context_fingerprint,
        "rationale": record.rationale,
        "stop": (
            {
                "stop_id": result.stop.stop_id,
                "stop_kind": result.stop.stop_kind.value,
                "reason": result.stop.reason,
                "resumable": result.stop.resumable,
                "approval_required": (
                    result.stop.approval_required
                ),
            }
            if result.stop is not None
            else None
        ),
        "ranked_candidates": [
            {
                "rank": ranked.rank,
                "candidate_id": ranked.candidate.candidate_id,
                "action_kind": ranked.candidate.action_kind.value,
                "total_score": ranked.assessment.total_score,
                "risk_score": ranked.assessment.risk_score,
                "confidence_score": (
                    ranked.assessment.confidence_score
                ),
                "evidence_score": (
                    ranked.assessment.evidence_score
                ),
                "utility_score": (
                    ranked.assessment.utility_score
                ),
                "reversibility_score": (
                    ranked.assessment.reversibility_score
                ),
            }
            for ranked in result.selection.ranked
        ],
        "created_at": record.created_at.isoformat(),
    }


def render_decision_markdown(
    result: DecisionResult,
) -> str:
    """Render a concise human-readable decision report."""
    summary = decision_summary(result)

    lines = [
        "# Aerion Forge Autonomous Decision",
        "",
        f"- Decision ID: `{summary['decision_id']}`",
        f"- Request ID: `{summary['request_id']}`",
        f"- Context ID: `{summary['context_id']}`",
        f"- Kind: `{summary['decision_kind']}`",
        f"- Disposition: `{summary['disposition']}`",
        (
            "- Selected candidate: "
            f"`{summary['selected_candidate_id']}`"
        ),
        f"- Approval required: `{summary['approval_required']}`",
        f"- Confidence: `{summary['confidence']}`",
        f"- Context fingerprint: `{summary['context_fingerprint']}`",
        "",
        "## Rationale",
        "",
        str(summary["rationale"]),
        "",
        "## Ranked Candidates",
        "",
    ]

    ranked_candidates = summary["ranked_candidates"]

    if ranked_candidates:
        for ranked in ranked_candidates:
            lines.append(
                f"{ranked['rank']}. "
                f"`{ranked['candidate_id']}` — "
                f"{ranked['action_kind']} — "
                f"score `{ranked['total_score']}`"
            )
    else:
        lines.append("_No acceptable candidates._")

    if summary["stop"] is not None:
        stop = summary["stop"]
        lines.extend(
            [
                "",
                "## Stop Decision",
                "",
                f"- Kind: `{stop['stop_kind']}`",
                f"- Resumable: `{stop['resumable']}`",
                f"- Reason: {stop['reason']}",
            ]
        )

    lines.append("")
    return "\n".join(lines)


def write_decision_report(
    result: DecisionResult,
    destination: Path,
) -> tuple[Path, Path]:
    """Write JSON and Markdown reports for one decision."""
    destination.mkdir(parents=True, exist_ok=True)

    json_path = destination / "AUTONOMOUS_DECISION.json"
    markdown_path = destination / "AUTONOMOUS_DECISION.md"

    json_path.write_text(
        json.dumps(
            decision_summary(result),
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        render_decision_markdown(result),
        encoding="utf-8",
    )

    return json_path, markdown_path
'@

Write-Utf8NoBom "forge\autonomous_decision\cli.py" @'
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
'@

Write-Utf8NoBom "tests\test_autonomous_decision_reporting.py" @'
from pathlib import Path

from forge.autonomous_decision.cli import sample_decision_result
from forge.autonomous_decision.reporting import (
    decision_summary,
    render_decision_markdown,
    write_decision_report,
)


def test_decision_summary_is_structured() -> None:
    summary = decision_summary(sample_decision_result())

    assert summary["decision_id"]
    assert summary["disposition"] == "select_action"
    assert summary["selected_candidate_id"] is not None
    assert summary["ranked_candidates"]


def test_no_safe_action_report_contains_stop() -> None:
    result = sample_decision_result(with_evidence=False)
    summary = decision_summary(result)
    report = render_decision_markdown(result)

    assert summary["disposition"] == "no_safe_action"
    assert summary["stop"] is not None
    assert "Stop Decision" in report


def test_write_decision_report(tmp_path: Path) -> None:
    json_path, markdown_path = write_decision_report(
        sample_decision_result(),
        tmp_path,
    )

    assert json_path.exists()
    assert markdown_path.exists()
    assert "select_action" in json_path.read_text(
        encoding="utf-8"
    )
'@

Write-Utf8NoBom "tests\test_autonomous_decision_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_decision.cli import app

runner = CliRunner()


def test_simulate_command() -> None:
    result = runner.invoke(app, ["simulate"])

    assert result.exit_code == 0
    normalized = " ".join(result.stdout.split())
    assert "Autonomous Decision Simulation" in normalized
    assert "select_action" in normalized


def test_simulate_without_evidence_stops() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--no-evidence"],
    )

    assert result.exit_code == 0
    assert "no_safe_action" in result.stdout


def test_report_sample_command() -> None:
    result = runner.invoke(app, ["report-sample"])

    assert result.exit_code == 0
    assert '"disposition": "select_action"' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.4-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_decision\ARCHITECTURE.md",
    ".\docs\autonomous_decision\SPECIFICATION.md",
    ".\docs\autonomous_decision\DATA_MODEL.md",
    ".\docs\autonomous_decision\DECISION_MODEL.md",
    ".\docs\autonomous_decision\CANDIDATE_MODEL.md",
    ".\docs\autonomous_decision\CONFIDENCE_MODEL.md",
    ".\docs\autonomous_decision\POLICY_MODEL.md",
    ".\docs\autonomous_decision\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_decision\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_decision\models.py",
    ".\forge\autonomous_decision\policies.py",
    ".\forge\autonomous_decision\candidate_generator.py",
    ".\forge\autonomous_decision\candidate_service.py",
    ".\forge\autonomous_decision\assessment_service.py",
    ".\forge\autonomous_decision\ranking.py",
    ".\forge\autonomous_decision\selector.py",
    ".\forge\autonomous_decision\decision_service.py",
    ".\forge\autonomous_decision\reporting.py",
    ".\forge\autonomous_decision\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.4 artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.4 artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_decision" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.4 architecture documents contain placeholders."
}

$Architecture = Get-Content `
    ".\docs\autonomous_decision\ARCHITECTURE.md" `
    -Raw

foreach ($RequiredPhrase in @(
    "No tool execution inside M5.4",
    "Candidate generation is bounded",
    "Every selected action has supporting evidence",
    "Decision records are immutable"
)) {
    if (-not $Architecture.Contains($RequiredPhrase)) {
        throw "M5.4 architecture principle missing: $RequiredPhrase"
    }
}

Write-Host "M5.4 architecture validation passed." `
    -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.4-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M5.4 architecture validation failed."
}

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff failed."
}

python -m mypy .
if ($LASTEXITCODE -ne 0) {
    throw "MyPy failed."
}

python -m pytest `
    .\tests\test_autonomous_decision_identifiers.py `
    .\tests\test_autonomous_decision_states.py `
    .\tests\test_autonomous_decision_policies.py `
    .\tests\test_autonomous_decision_models.py `
    .\tests\test_autonomous_decision_candidate_generator.py `
    .\tests\test_autonomous_decision_deduplication.py `
    .\tests\test_autonomous_decision_feasibility.py `
    .\tests\test_autonomous_decision_policy_filter.py `
    .\tests\test_autonomous_decision_candidate_service.py `
    .\tests\test_autonomous_decision_risk_assessor.py `
    .\tests\test_autonomous_decision_confidence_assessor.py `
    .\tests\test_autonomous_decision_evidence_assessor.py `
    .\tests\test_autonomous_decision_scoring.py `
    .\tests\test_autonomous_decision_assessment_service.py `
    .\tests\test_autonomous_decision_ranking.py `
    .\tests\test_autonomous_decision_selector.py `
    .\tests\test_autonomous_decision_rationale.py `
    .\tests\test_autonomous_decision_replay_guard.py `
    .\tests\test_autonomous_decision_decision_journal.py `
    .\tests\test_autonomous_decision_decision_service.py `
    .\tests\test_autonomous_decision_reporting.py `
    .\tests\test_autonomous_decision_cli.py `
    -p no:cacheprovider

if ($LASTEXITCODE -ne 0) {
    throw "M5.4 focused test suite failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Full repository test suite failed."
}

Write-Host "M5.4 completion validation passed." `
    -ForegroundColor Green
'@

$RootCliPath = Join-Path $RepositoryRoot "forge\cli.py"
$ImportLine = 'from forge.autonomous_decision.cli import app as autonomous_decision_app'
$RegistrationLine = 'app.add_typer(autonomous_decision_app, name="decide")'

$CliLines = @(
    Get-Content $RootCliPath |
        Where-Object {
            $_.Trim() -ne $ImportLine -and
            $_.Trim() -ne $RegistrationLine
        }
)

$AppIndex = -1

for ($Index = 0; $Index -lt $CliLines.Count; $Index++) {
    if ($CliLines[$Index] -match '^app\s*=\s*typer\.Typer\(') {
        $AppIndex = $Index
        break
    }
}

if ($AppIndex -lt 0) {
    throw "Root Typer application declaration not found in forge\cli.py."
}

$BeforeApp = @()
if ($AppIndex -gt 0) {
    $BeforeApp = @($CliLines[0..($AppIndex - 1)])
}

$FromApp = @($CliLines[$AppIndex..($CliLines.Count - 1)])

$CliLines = @(
    $BeforeApp
    $ImportLine
    ''
    $FromApp
)

$CommandIndex = -1

for ($Index = 0; $Index -lt $CliLines.Count; $Index++) {
    if ($CliLines[$Index] -match '^@app\.(command|callback)\b') {
        $CommandIndex = $Index
        break
    }
}

if ($CommandIndex -lt 0) {
    throw "No root CLI command decorator found in forge\cli.py."
}

$BeforeCommand = @()
if ($CommandIndex -gt 0) {
    $BeforeCommand = @($CliLines[0..($CommandIndex - 1)])
}

$FromCommand = @($CliLines[$CommandIndex..($CliLines.Count - 1)])

$CliLines = @(
    $BeforeCommand
    $RegistrationLine
    ''
    $FromCommand
)

[System.IO.File]::WriteAllLines(
    $RootCliPath,
    $CliLines,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Host ""
Write-Host "M5.4 Package 4 files written. Running validation..." `
    -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_autonomous_decision_reporting.py `
    .\tests\test_autonomous_decision_cli.py `
    -p no:cacheprovider
Assert-CommandSuccess "M5.4 Package 4 focused tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.4 architecture validation"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.4-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.4 completion validation"

Write-Host ""
Write-Host "M5.4 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short
