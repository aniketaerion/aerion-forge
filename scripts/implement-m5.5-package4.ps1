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

    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

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

$ExpectedBranch = "feature/m5.5-autonomous-memory-learning"
$CurrentBranch = git branch --show-current
Assert-CommandSuccess "Read current branch"

if ($CurrentBranch -ne $ExpectedBranch) {
    throw "M5.5 Package 4 must run on '$ExpectedBranch'. Current branch: '$CurrentBranch'."
}

Write-Utf8NoBom "forge\autonomous_memory\reporting.py" @'
"""Reporting for autonomous memory and learning."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from forge.autonomous_memory.models import (
    LearningRecord,
    MemoryMatch,
    MemoryRecord,
)


@dataclass(frozen=True, slots=True)
class MemoryReport:
    """Serializable memory report."""

    records: tuple[MemoryRecord, ...]
    matches: tuple[MemoryMatch, ...]
    learning: tuple[LearningRecord, ...]


def memory_report_payload(
    report: MemoryReport,
) -> dict[str, Any]:
    """Return deterministic JSON-ready report payload."""
    return {
        "record_count": len(report.records),
        "match_count": len(report.matches),
        "learning_count": len(report.learning),
        "records": [
            record.model_dump(mode="json")
            for record in sorted(
                report.records,
                key=lambda item: item.memory_id,
            )
        ],
        "matches": [
            match.model_dump(mode="json")
            for match in sorted(
                report.matches,
                key=lambda item: (
                    -item.total_score,
                    item.memory_id,
                ),
            )
        ],
        "learning": [
            learning.model_dump(mode="json")
            for learning in sorted(
                report.learning,
                key=lambda item: item.learning_id,
            )
        ],
    }


def memory_report_json(
    report: MemoryReport,
) -> str:
    """Render memory report as JSON."""
    return json.dumps(
        memory_report_payload(report),
        indent=2,
        sort_keys=True,
    )


def memory_report_markdown(
    report: MemoryReport,
) -> str:
    """Render memory report as Markdown."""
    lines = [
        "# Autonomous Memory Report",
        "",
        f"- Records: {len(report.records)}",
        f"- Matches: {len(report.matches)}",
        f"- Learning records: {len(report.learning)}",
        "",
        "## Memory Records",
        "",
    ]

    for record in sorted(
        report.records,
        key=lambda item: item.memory_id,
    ):
        lines.extend(
            [
                f"### {record.memory_id}",
                "",
                f"- Kind: `{record.memory_kind.value}`",
                f"- Status: `{record.status.value}`",
                f"- Confidence: `{record.confidence:.3f}`",
                f"- Repository: `{record.repository_scope}`",
                "",
                record.statement,
                "",
            ]
        )

    lines.extend(["## Learning Records", ""])

    for learning in sorted(
        report.learning,
        key=lambda item: item.learning_id,
    ):
        lines.extend(
            [
                f"### {learning.learning_id}",
                "",
                f"- Successes: `{learning.success_count}`",
                f"- Failures: `{learning.failure_count}`",
                f"- Confidence: `{learning.confidence:.3f}`",
                "",
                learning.lesson,
                "",
            ]
        )

    return "\n".join(lines).rstrip() + "\n"
'@

Write-Utf8NoBom "forge\autonomous_memory\cli.py" @'
"""CLI commands for autonomous memory inspection."""

from __future__ import annotations

import json

import typer

from forge.autonomous_memory.indexing import MemoryIndex
from forge.autonomous_memory.memory_service import (
    AutonomousMemoryService,
)
from forge.autonomous_memory.models import (
    MemoryObservation,
    MemoryQuery,
)
from forge.autonomous_memory.policies import (
    AutonomousMemoryPolicy,
)
from forge.autonomous_memory.reporting import (
    MemoryReport,
    memory_report_json,
    memory_report_markdown,
)
from forge.autonomous_memory.states import MemorySourceKind
from forge.autonomous_memory.storage import (
    InMemoryMemoryStorage,
)

app = typer.Typer(
    help="Inspect and simulate autonomous memory behaviour."
)


def _sample_service() -> AutonomousMemoryService:
    service = AutonomousMemoryService(
        policy=AutonomousMemoryPolicy(),
        storage=InMemoryMemoryStorage(),
        index=MemoryIndex(),
    )
    service.ingest(
        MemoryObservation(
            observation_id="sample-observation-1",
            source_kind=MemorySourceKind.REPOSITORY,
            source_reference="forge/sample.py",
            repository_root="sample-repository",
            repository_fingerprint="sample-fingerprint",
            content="Repository uses Python.",
            evidence_references=("sample-evidence-1",),
            tags=("sample", "python"),
        ),
        actor="Aerion Forge",
    )
    return service


@app.command("simulate")
def simulate_memory(
    query_text: str = typer.Option(
        "python repository",
        "--query",
        help="Text used for read-only memory retrieval.",
    ),
    output_format: str = typer.Option(
        "json",
        "--format",
        help="Output format: json or markdown.",
    ),
) -> None:
    """Run an in-memory read-only retrieval simulation."""
    service = _sample_service()
    result = service.retrieve(
        query=MemoryQuery(
            query_id="sample-query-1",
            repository_scope="sample-repository",
            requested_by="cli",
        ),
        query_text=query_text,
    )

    report = MemoryReport(
        records=result.records,
        matches=result.matches,
        learning=service.storage.all_learning(),
    )

    if output_format == "markdown":
        typer.echo(memory_report_markdown(report))
        return

    if output_format != "json":
        raise typer.BadParameter(
            "Format must be 'json' or 'markdown'."
        )

    typer.echo(memory_report_json(report))


@app.command("policy")
def show_policy() -> None:
    """Show the default-safe autonomous-memory policy."""
    payload = AutonomousMemoryPolicy().model_dump(
        mode="json"
    )
    typer.echo(
        json.dumps(
            payload,
            indent=2,
            sort_keys=True,
        )
    )
'@

Write-Utf8NoBom "tests\test_autonomous_memory_reporting.py" @'
import json

from forge.autonomous_memory.models import (
    MemoryApplicability,
    MemoryRecord,
)
from forge.autonomous_memory.reporting import (
    MemoryReport,
    memory_report_json,
    memory_report_markdown,
)
from forge.autonomous_memory.states import (
    ApplicabilityKind,
    MemoryKind,
    RetentionClass,
)


def record() -> MemoryRecord:
    return MemoryRecord(
        memory_id="memory-1",
        memory_kind=MemoryKind.REPOSITORY_FACT,
        statement="Repository uses Python.",
        normalized_statement="repository uses python",
        confidence=0.9,
        repository_scope="repository",
        evidence_references=("evidence-1",),
        source_references=("source-1",),
        applicability=MemoryApplicability(
            kind=ApplicabilityKind.EXACT_REPOSITORY,
            repository_scope="repository",
            rationale="Repository scoped.",
        ),
        retention_class=RetentionClass.PROJECT_LIFETIME,
    )


def test_json_report_is_serializable() -> None:
    payload = json.loads(
        memory_report_json(
            MemoryReport(
                records=(record(),),
                matches=(),
                learning=(),
            )
        )
    )

    assert payload["record_count"] == 1
    assert payload["records"][0]["memory_id"] == "memory-1"


def test_markdown_report_contains_record() -> None:
    markdown = memory_report_markdown(
        MemoryReport(
            records=(record(),),
            matches=(),
            learning=(),
        )
    )

    assert "# Autonomous Memory Report" in markdown
    assert "memory-1" in markdown
'@

Write-Utf8NoBom "tests\test_autonomous_memory_cli.py" @'
from typer.testing import CliRunner

from forge.autonomous_memory.cli import app


runner = CliRunner()


def test_memory_simulation_outputs_json() -> None:
    result = runner.invoke(
        app,
        ["simulate", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"record_count": 1' in result.stdout


def test_memory_policy_command_outputs_policy() -> None:
    result = runner.invoke(app, ["policy"])

    assert result.exit_code == 0
    assert '"reject_secrets": true' in result.stdout
'@

Write-Utf8NoBom "scripts\validate-m5.5-architecture.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_memory\ARCHITECTURE.md",
    ".\docs\autonomous_memory\SPECIFICATION.md",
    ".\docs\autonomous_memory\DATA_MODEL.md",
    ".\docs\autonomous_memory\MEMORY_MODEL.md",
    ".\docs\autonomous_memory\RETRIEVAL_MODEL.md",
    ".\docs\autonomous_memory\LEARNING_MODEL.md",
    ".\docs\autonomous_memory\RETENTION_MODEL.md",
    ".\docs\autonomous_memory\POLICY_MODEL.md",
    ".\docs\autonomous_memory\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_memory\DECISIONS.md"
)

foreach ($Path in $RequiredDocs) {
    if (-not (Test-Path $Path)) {
        throw "Missing architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 300) {
        throw "Architecture document too small: $Path"
    }
}

$RequiredModules = @(
    ".\forge\autonomous_memory\models.py",
    ".\forge\autonomous_memory\policies.py",
    ".\forge\autonomous_memory\ingestion.py",
    ".\forge\autonomous_memory\storage.py",
    ".\forge\autonomous_memory\retrieval.py",
    ".\forge\autonomous_memory\learning.py",
    ".\forge\autonomous_memory\reporting.py",
    ".\forge\autonomous_memory\cli.py"
)

foreach ($Path in $RequiredModules) {
    if (-not (Test-Path $Path)) {
        throw "Missing implementation module: $Path"
    }
}

Write-Host "M5.5 architecture validation passed." `
    -ForegroundColor Green
'@

Write-Utf8NoBom "scripts\validate-m5.5-completion.ps1" @'
[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-Success {
    param([string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-Success "M5.5 architecture validation"

python -m ruff check .
Assert-Success "Ruff"

python -m mypy .
Assert-Success "MyPy"

python -m pytest `
    .\tests\test_autonomous_memory_identifiers.py `
    .\tests\test_autonomous_memory_states.py `
    .\tests\test_autonomous_memory_policies.py `
    .\tests\test_autonomous_memory_models.py `
    .\tests\test_autonomous_memory_normalization.py `
    .\tests\test_autonomous_memory_redaction.py `
    .\tests\test_autonomous_memory_provenance.py `
    .\tests\test_autonomous_memory_classification.py `
    .\tests\test_autonomous_memory_deduplication.py `
    .\tests\test_autonomous_memory_ingestion.py `
    .\tests\test_autonomous_memory_storage.py `
    .\tests\test_autonomous_memory_repository.py `
    .\tests\test_autonomous_memory_indexing.py `
    .\tests\test_autonomous_memory_search.py `
    .\tests\test_autonomous_memory_retrieval.py `
    .\tests\test_autonomous_memory_retention.py `
    .\tests\test_autonomous_memory_service.py `
    .\tests\test_autonomous_memory_supersession.py `
    .\tests\test_autonomous_memory_feedback.py `
    .\tests\test_autonomous_memory_learning.py `
    .\tests\test_autonomous_memory_consolidation.py `
    .\tests\test_autonomous_memory_learning_service.py `
    .\tests\test_autonomous_memory_reporting.py `
    .\tests\test_autonomous_memory_cli.py `
    -p no:cacheprovider
Assert-Success "M5.5 focused tests"

python -m pytest -p no:cacheprovider
Assert-Success "Full repository tests"

Write-Host "M5.5 completion validation passed." `
    -ForegroundColor Green
'@

$RootCliPath = ".\forge\cli.py"

if (-not (Test-Path $RootCliPath)) {
    throw "Missing root CLI file: $RootCliPath"
}

$CliContent = Get-Content $RootCliPath -Raw

$ImportLine = "from forge.autonomous_memory.cli import app as autonomous_memory_app"
$RegistrationLine = 'app.add_typer(autonomous_memory_app, name="autonomous-memory")'

if (-not $CliContent.Contains($ImportLine)) {
    $CliContent = $ImportLine + [Environment]::NewLine + $CliContent
}

if (-not $CliContent.Contains($RegistrationLine)) {
    $CliContent = $CliContent.TrimEnd() + `
        [Environment]::NewLine + `
        $RegistrationLine + `
        [Environment]::NewLine
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $RootCliPath),
    $CliContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\cli.py" -ForegroundColor Green

Write-Host ""
Write-Host "M5.5 Package 4 files written. Running validation..." `
    -ForegroundColor Cyan

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m5.5-completion.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "M5.5 completion validation"

Write-Host ""
Write-Host "M5.5 PACKAGE 4 COMPLETE" -ForegroundColor Green

git status --short