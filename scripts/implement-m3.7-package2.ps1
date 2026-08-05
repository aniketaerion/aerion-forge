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

Write-Utf8NoBom "forge\build_verification\evidence.py" @'
"""Evidence construction for M3.7 Build Verification."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.identifiers import (
    verification_evidence_identifier,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStepResult,
)


def repository_fingerprint(
    repository_root: Path,
    target_paths: tuple[str, ...],
) -> str:
    """Hash bounded repository content deterministically."""
    root = repository_root.resolve()
    digest = hashlib.sha256()

    selected = target_paths or (".",)

    for relative_path in sorted(selected):
        candidate = (root / relative_path).resolve()
        candidate.relative_to(root)

        if candidate.is_file():
            digest.update(relative_path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(candidate.read_bytes())
            digest.update(b"\0")
            continue

        if candidate.is_dir():
            for file_path in sorted(
                path
                for path in candidate.rglob("*")
                if path.is_file()
                and ".git" not in path.parts
                and "__pycache__" not in path.parts
            ):
                relative = file_path.relative_to(root).as_posix()
                digest.update(relative.encode("utf-8"))
                digest.update(b"\0")
                digest.update(file_path.read_bytes())
                digest.update(b"\0")

    return digest.hexdigest()


def aggregate_status(
    results: tuple[VerificationStepResult, ...],
) -> VerificationStatus:
    """Aggregate step results using fail-closed precedence."""
    statuses = {result.status for result in results}

    if VerificationStatus.TIMED_OUT in statuses:
        return VerificationStatus.TIMED_OUT
    if VerificationStatus.BLOCKED in statuses:
        return VerificationStatus.BLOCKED
    if VerificationStatus.FAILED in statuses:
        return VerificationStatus.FAILED
    if VerificationStatus.CANCELLED in statuses:
        return VerificationStatus.CANCELLED
    if results and all(
        result.status is VerificationStatus.PASSED
        for result in results
    ):
        return VerificationStatus.PASSED

    return VerificationStatus.RUNNING


def build_evidence(
    request: BuildVerificationRequest,
    results: tuple[VerificationStepResult, ...],
    *,
    repository_root: Path,
    started_at: datetime,
    completed_at: datetime | None = None,
) -> BuildVerificationEvidence:
    """Construct deterministic build-verification evidence."""
    status = aggregate_status(results)
    terminal = status in {
        VerificationStatus.PASSED,
        VerificationStatus.FAILED,
        VerificationStatus.BLOCKED,
        VerificationStatus.TIMED_OUT,
        VerificationStatus.CANCELLED,
    }

    finished_at = completed_at
    if terminal and finished_at is None:
        finished_at = datetime.now(UTC)

    fingerprint = repository_fingerprint(
        repository_root,
        request.target_paths,
    )

    evidence_id = verification_evidence_identifier(
        {
            "request_id": request.request_id,
            "source_revision": request.source_revision,
            "repository_fingerprint": fingerprint,
            "status": status.value,
            "results": [
                {
                    "step_id": result.step_id,
                    "status": result.status.value,
                    "exit_code": result.exit_code,
                }
                for result in results
            ],
        }
    )

    return BuildVerificationEvidence(
        evidence_id=evidence_id,
        request=request,
        status=status,
        step_results=results,
        repository_fingerprint=fingerprint,
        started_at=started_at,
        completed_at=finished_at,
    )
'@

Write-Utf8NoBom "forge\build_verification\decision.py" @'
"""Release-gate decision engine for M3.7 Build Verification."""

from __future__ import annotations

from forge.build_verification.identifiers import (
    release_decision_identifier,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    ReleaseDecision,
    ReleaseGateDecision,
    VerificationStatus,
)
from forge.build_verification.policies import blocking_finding_ids


def decide_release(
    evidence: BuildVerificationEvidence,
    policy: BuildVerificationPolicy,
) -> ReleaseGateDecision:
    """Create a deterministic release decision from evidence."""
    findings = tuple(
        finding
        for result in evidence.step_results
        for finding in result.findings
    )
    blocking = blocking_finding_ids(findings, policy)

    required_steps = {
        step.step_id
        for step in evidence.request.steps
        if step.required
    }
    passed_steps = {
        result.step_id
        for result in evidence.step_results
        if result.status is VerificationStatus.PASSED
    }
    missing_required = tuple(sorted(required_steps - passed_steps))

    reasons: list[str] = []

    if evidence.status is not VerificationStatus.PASSED:
        reasons.append(
            f"verification evidence status is {evidence.status.value}"
        )

    if missing_required:
        reasons.append(
            "required verification steps did not pass: "
            + ", ".join(missing_required)
        )

    if blocking:
        reasons.append(
            "blocking verification findings exist: "
            + ", ".join(blocking)
        )

    if reasons:
        decision = ReleaseDecision.REJECTED
    elif not evidence.step_results:
        decision = ReleaseDecision.MANUAL_REVIEW
        reasons.append("verification evidence contains no step results")
    else:
        decision = ReleaseDecision.APPROVED
        reasons.append("all required verification gates passed")

    decision_id = release_decision_identifier(
        {
            "evidence_id": evidence.evidence_id,
            "decision": decision.value,
            "reasons": reasons,
            "blocking_findings": blocking,
        }
    )

    return ReleaseGateDecision(
        decision_id=decision_id,
        evidence_id=evidence.evidence_id,
        decision=decision,
        reasons=tuple(reasons),
        blocking_findings=blocking,
    )
'@

Write-Utf8NoBom "forge\build_verification\pipeline.py" @'
"""Ordered verification pipeline for M3.7 Build Verification."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    BuildVerificationRequest,
    ReleaseGateDecision,
    VerificationStatus,
    VerificationStepResult,
)
from forge.build_verification.policies import validate_request
from forge.build_verification.registry import (
    BuildVerificationProviderRegistry,
)
from forge.build_verification.runner import run_step


class BuildVerificationPipeline:
    """Execute a bounded verification request in declared order."""

    def __init__(
        self,
        policy: BuildVerificationPolicy | None = None,
        registry: BuildVerificationProviderRegistry | None = None,
    ) -> None:
        self.policy = policy or BuildVerificationPolicy()
        self.registry = registry or BuildVerificationProviderRegistry()

    def execute(
        self,
        request: BuildVerificationRequest,
    ) -> tuple[BuildVerificationEvidence, ReleaseGateDecision]:
        """Run all verification steps and return evidence plus decision."""
        validate_request(request, self.policy)

        root = Path(request.repository_root).resolve()
        started_at = datetime.now(UTC)
        results: list[VerificationStepResult] = []

        for step in request.steps:
            result = run_step(
                root,
                step,
                self.policy,
                self.registry,
            )
            results.append(result)

            if (
                step.required
                and result.status is not VerificationStatus.PASSED
            ):
                break

        evidence = build_evidence(
            request,
            tuple(results),
            repository_root=root,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
        decision = decide_release(evidence, self.policy)

        return evidence, decision
'@

Write-Utf8NoBom "tests\test_build_verification_evidence.py" @'
from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.evidence import (
    aggregate_status,
    build_evidence,
    repository_fingerprint,
)
from forge.build_verification.models import (
    BuildVerificationRequest,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)


def request_for(tmp_path: Path) -> BuildVerificationRequest:
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    return BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )


def test_repository_fingerprint_changes_with_content(
    tmp_path: Path,
) -> None:
    target = tmp_path / "sample.py"
    target.write_text("value = 1\n", encoding="utf-8")
    first = repository_fingerprint(tmp_path, ("sample.py",))

    target.write_text("value = 2\n", encoding="utf-8")
    second = repository_fingerprint(tmp_path, ("sample.py",))

    assert first != second


def test_aggregate_status_is_fail_closed() -> None:
    passed = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )
    failed = VerificationStepResult(
        step_id="pytest",
        status=VerificationStatus.FAILED,
        exit_code=1,
        completed_at=datetime.now(UTC),
    )

    assert aggregate_status((passed, failed)) is VerificationStatus.FAILED


def test_evidence_identifier_is_deterministic(tmp_path: Path) -> None:
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    request = request_for(tmp_path)
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime(2026, 1, 1, tzinfo=UTC),
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)

    first = build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )
    second = build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )

    assert first.evidence_id == second.evidence_id
'@

Write-Utf8NoBom "tests\test_build_verification_decision.py" @'
from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    ReleaseDecision,
    VerificationFinding,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)


def evidence_for(
    tmp_path: Path,
    result: VerificationStepResult,
):
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )
    started = datetime(2026, 1, 1, tzinfo=UTC)
    return build_evidence(
        request,
        (result,),
        repository_root=tmp_path,
        started_at=started,
        completed_at=started,
    )


def test_release_is_approved_when_required_step_passes(
    tmp_path: Path,
) -> None:
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        completed_at=datetime.now(UTC),
    )

    decision = decide_release(
        evidence_for(tmp_path, result),
        BuildVerificationPolicy(),
    )

    assert decision.decision is ReleaseDecision.APPROVED


def test_release_is_rejected_when_required_step_fails(
    tmp_path: Path,
) -> None:
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.FAILED,
        exit_code=1,
        completed_at=datetime.now(UTC),
    )

    decision = decide_release(
        evidence_for(tmp_path, result),
        BuildVerificationPolicy(),
    )

    assert decision.decision is ReleaseDecision.REJECTED


def test_high_finding_rejects_release(tmp_path: Path) -> None:
    finding = VerificationFinding(
        finding_id="finding-1",
        step_id="ruff",
        severity=FindingSeverity.HIGH,
        code="TEST",
        message="blocking",
    )
    result = VerificationStepResult(
        step_id="ruff",
        status=VerificationStatus.PASSED,
        exit_code=0,
        findings=(finding,),
        completed_at=datetime.now(UTC),
    )

    decision = decide_release(
        evidence_for(tmp_path, result),
        BuildVerificationPolicy(),
    )

    assert decision.decision is ReleaseDecision.REJECTED
    assert decision.blocking_findings == ("finding-1",)
'@

Write-Utf8NoBom "tests\test_build_verification_pipeline.py" @'
from pathlib import Path

from forge.build_verification.models import (
    BuildVerificationRequest,
    ReleaseDecision,
    VerificationStatus,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.pipeline import BuildVerificationPipeline


def test_pipeline_approves_passing_verification(
    tmp_path: Path,
) -> None:
    (tmp_path / "sample.py").write_text(
        "value = 1\n",
        encoding="utf-8",
    )
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(step,),
        target_paths=("sample.py",),
    )

    evidence, decision = BuildVerificationPipeline().execute(request)

    assert evidence.status is VerificationStatus.PASSED
    assert decision.decision is ReleaseDecision.APPROVED


def test_pipeline_stops_after_required_failure(
    tmp_path: Path,
) -> None:
    (tmp_path / "bad.py").write_text(
        "import os\n",
        encoding="utf-8",
    )
    first = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("bad.py",),
    )
    second = VerificationStep(
        step_id="pytest",
        tool=VerificationTool.PYTEST,
        name="Pytest",
        arguments=("-q",),
    )
    request = BuildVerificationRequest(
        request_id="request-2",
        repository_root=str(tmp_path),
        source_revision="abc",
        objective="verify",
        steps=(first, second),
        target_paths=("bad.py",),
    )

    evidence, decision = BuildVerificationPipeline().execute(request)

    assert evidence.status is VerificationStatus.FAILED
    assert len(evidence.step_results) == 1
    assert decision.decision is ReleaseDecision.REJECTED
'@

Write-Host ""
Write-Host "M3.7 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_build_verification_pipeline.py `
    .\tests\test_build_verification_evidence.py `
    .\tests\test_build_verification_decision.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.7 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.7 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short