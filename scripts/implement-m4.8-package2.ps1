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

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\coverage.py" @'
"""Test-count and coverage validation for M4.8 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def coverage_check() -> PhaseValidationCheck:
    payload = {
        "name": "Coverage validation",
        "kind": PhaseValidationKind.COVERAGE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Coverage validation",
        kind=PhaseValidationKind.COVERAGE,
        description=(
            "Validate collected test count and configured coverage "
            "thresholds."
        ),
    )


def validate_coverage(
    *,
    collected_test_count: int,
    minimum_test_count: int,
    coverage_percent: float | None,
    minimum_coverage_percent: float,
) -> PhaseValidationResult:
    check = coverage_check()

    tests_pass = collected_test_count >= minimum_test_count
    coverage_required = minimum_coverage_percent > 0.0

    if not coverage_required:
        coverage_pass = True
    elif coverage_percent is None:
        coverage_pass = False
    else:
        coverage_pass = (
            coverage_percent >= minimum_coverage_percent
        )
    passed = tests_pass and coverage_pass
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )

    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "collected_test_count": collected_test_count,
        "minimum_test_count": minimum_test_count,
        "coverage_percent": coverage_percent,
        "minimum_coverage_percent": minimum_coverage_percent,
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Coverage and test-count requirements passed."
            if passed
            else "Coverage or test-count requirements failed."
        ),
        evidence={
            "collected_test_count": str(collected_test_count),
            "minimum_test_count": str(minimum_test_count),
            "coverage_percent": (
                "not-provided"
                if coverage_percent is None
                else f"{coverage_percent:.2f}"
            ),
            "minimum_coverage_percent": (
                f"{minimum_coverage_percent:.2f}"
            ),
        },
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\compatibility.py" @'
"""Compatibility validation for M4.8 Package 2."""

from __future__ import annotations

from collections.abc import Iterable

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def compatibility_check() -> PhaseValidationCheck:
    payload = {
        "name": "Compatibility validation",
        "kind": PhaseValidationKind.COMPATIBILITY.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Compatibility validation",
        kind=PhaseValidationKind.COMPATIBILITY,
        description=(
            "Validate that required compatibility markers are "
            "present in the repository baseline."
        ),
    )


def validate_compatibility(
    *,
    required_markers: Iterable[str],
    available_markers: Iterable[str],
) -> PhaseValidationResult:
    check = compatibility_check()
    required = tuple(sorted(set(required_markers)))
    available = set(available_markers)
    missing = tuple(
        marker
        for marker in required
        if marker not in available
    )
    passed = not missing
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )

    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "required_markers": required,
        "missing_markers": missing,
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Compatibility requirements passed."
            if passed
            else "Compatibility requirements are incomplete."
        ),
        evidence={
            "required_markers": ",".join(required),
            "missing_markers": ",".join(missing),
        },
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\phase_validation\release.py" @'
"""Release-readiness validation for M4.8 Package 2."""

from __future__ import annotations

from forge.domain_intelligence.phase_validation.identifiers import (
    phase_release_manifest_identifier,
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseReleaseManifest,
    PhaseValidationCheck,
    PhaseValidationKind,
    PhaseValidationResult,
    PhaseValidationStatus,
)


def release_check() -> PhaseValidationCheck:
    payload = {
        "name": "Release readiness validation",
        "kind": PhaseValidationKind.RELEASE.value,
    }
    return PhaseValidationCheck(
        check_id=phase_validation_check_identifier(payload),
        name="Release readiness validation",
        kind=PhaseValidationKind.RELEASE,
        description=(
            "Validate branch, commit, working-tree, and release-tag "
            "requirements."
        ),
    )


def validate_release_readiness(
    *,
    branch: str,
    commit: str,
    worktree_clean: bool,
    require_clean_worktree: bool,
    tag: str | None,
    require_release_tag: bool,
) -> PhaseValidationResult:
    check = release_check()

    clean_pass = (
        worktree_clean
        if require_clean_worktree
        else True
    )
    tag_pass = (
        bool(tag)
        if require_release_tag
        else True
    )
    passed = bool(branch and commit) and clean_pass and tag_pass
    status = (
        PhaseValidationStatus.PASS
        if passed
        else PhaseValidationStatus.FAIL
    )

    payload = {
        "check_id": check.check_id,
        "status": status.value,
        "branch": branch,
        "commit": commit,
        "worktree_clean": worktree_clean,
        "tag": tag,
    }

    return PhaseValidationResult(
        result_id=phase_validation_result_identifier(payload),
        check_id=check.check_id,
        status=status,
        message=(
            "Release-readiness requirements passed."
            if passed
            else "Release-readiness requirements failed."
        ),
        evidence={
            "branch": branch,
            "commit": commit,
            "worktree_clean": str(worktree_clean).lower(),
            "tag": tag or "",
            "require_release_tag": str(
                require_release_tag
            ).lower(),
        },
    )


def build_release_manifest(
    *,
    phase: str,
    milestone: str | None,
    branch: str,
    commit: str,
    tag: str | None,
    validation_result_ids: tuple[str, ...],
) -> PhaseReleaseManifest:
    payload = {
        "phase": phase,
        "milestone": milestone,
        "branch": branch,
        "commit": commit,
        "tag": tag,
        "validation_result_ids": validation_result_ids,
    }

    return PhaseReleaseManifest(
        manifest_id=phase_release_manifest_identifier(payload),
        phase=phase,
        milestone=milestone,
        branch=branch,
        commit=commit,
        tag=tag,
        validation_result_ids=validation_result_ids,
    )
'@

$RegistryPath = ".\forge\domain_intelligence\phase_validation\registry.py"
$RegistryContent = Get-Content $RegistryPath -Raw

if (
    $RegistryContent -notmatch
    'from forge\.domain_intelligence\.phase_validation\.coverage import'
) {
    $ImportAnchor = @'
from forge.domain_intelligence.phase_validation.architecture import (
    architecture_check,
    validate_architecture,
)
'@

    $ImportBlock = @'
from forge.domain_intelligence.phase_validation.architecture import (
    architecture_check,
    validate_architecture,
)
from forge.domain_intelligence.phase_validation.compatibility import (
    compatibility_check,
)
from forge.domain_intelligence.phase_validation.coverage import (
    coverage_check,
)
from forge.domain_intelligence.phase_validation.release import (
    release_check,
)
'@

    if (-not $RegistryContent.Contains($ImportAnchor)) {
        throw "Registry import anchor not found."
    }

    $RegistryContent = $RegistryContent.Replace(
        $ImportAnchor,
        $ImportBlock
    )
}

$DefaultAnchor = @'
        registry.register(
            acceptance_check(),
            _run_acceptance,
        )
        return registry
'@

$DefaultReplacement = @'
        registry.register(
            acceptance_check(),
            _run_acceptance,
        )
        registry.register_placeholder(coverage_check())
        registry.register_placeholder(compatibility_check())
        registry.register_placeholder(release_check())
        return registry
'@

if (
    $RegistryContent -notmatch
    'register_placeholder\(coverage_check\(\)\)'
) {
    if (-not $RegistryContent.Contains($DefaultAnchor)) {
        throw "Registry default anchor not found."
    }

    $RegistryContent = $RegistryContent.Replace(
        $DefaultAnchor,
        $DefaultReplacement
    )
}

$RegisterAnchor = @'
    def register(
        self,
        check: PhaseValidationCheck,
        runner: ValidationRunner,
    ) -> None:
        self._entries[check.check_id] = (check, runner)

'@

$RegisterReplacement = @'
    def register(
        self,
        check: PhaseValidationCheck,
        runner: ValidationRunner,
    ) -> None:
        self._entries[check.check_id] = (check, runner)

    def register_placeholder(
        self,
        check: PhaseValidationCheck,
    ) -> None:
        def _unsupported(
            repository_root: Path,
            phase: str,
        ) -> PhaseValidationResult:
            del repository_root, phase
            raise RuntimeError(
                f"Validation runner not configured: {check.name}"
            )

        self._entries[check.check_id] = (
            check,
            _unsupported,
        )

'@

if (
    $RegistryContent -notmatch
    'def register_placeholder'
) {
    if (-not $RegistryContent.Contains($RegisterAnchor)) {
        throw "Registry register anchor not found."
    }

    $RegistryContent = $RegistryContent.Replace(
        $RegisterAnchor,
        $RegisterReplacement
    )
}

$ExecuteOld = @'
    def execute(
        self,
        repository_root: Path,
        phase: str,
    ) -> tuple[PhaseValidationResult, ...]:
        return tuple(
            runner(repository_root, phase)
            for _, runner in (
                entry
                for _, entry in sorted(
                    self._entries.items(),
                    key=lambda item: (
                        item[1][0].kind.value,
                        item[1][0].name,
                    ),
                )
            )
        )
'@

$ExecuteNew = @'
    def execute(
        self,
        repository_root: Path,
        phase: str,
        *,
        kinds: tuple[str, ...] = (),
    ) -> tuple[PhaseValidationResult, ...]:
        requested = set(kinds)

        return tuple(
            runner(repository_root, phase)
            for check, runner in (
                entry
                for _, entry in sorted(
                    self._entries.items(),
                    key=lambda item: (
                        item[1][0].kind.value,
                        item[1][0].name,
                    ),
                )
            )
            if not requested or check.kind.value in requested
        )
'@

if ($RegistryContent.Contains($ExecuteOld)) {
    $RegistryContent = $RegistryContent.Replace(
        $ExecuteOld,
        $ExecuteNew
    )
}

[System.IO.File]::WriteAllText(
    (Resolve-Path $RegistryPath),
    $RegistryContent,
    [System.Text.UTF8Encoding]::new($false)
)

Write-Host "UPDATED forge\domain_intelligence\phase_validation\registry.py" -ForegroundColor Green

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_coverage.py" @'
from forge.domain_intelligence.phase_validation.coverage import (
    validate_coverage,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)


def test_coverage_validation_passes() -> None:
    result = validate_coverage(
        collected_test_count=100,
        minimum_test_count=50,
        coverage_percent=85.0,
        minimum_coverage_percent=80.0,
    )

    assert result.status is PhaseValidationStatus.PASS


def test_coverage_validation_fails_without_required_coverage() -> None:
    result = validate_coverage(
        collected_test_count=100,
        minimum_test_count=50,
        coverage_percent=None,
        minimum_coverage_percent=80.0,
    )

    assert result.status is PhaseValidationStatus.FAIL
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_compatibility.py" @'
from forge.domain_intelligence.phase_validation.compatibility import (
    validate_compatibility,
)
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)


def test_compatibility_validation_passes() -> None:
    result = validate_compatibility(
        required_markers=("python", "powershell"),
        available_markers=("python", "powershell", "git"),
    )

    assert result.status is PhaseValidationStatus.PASS


def test_compatibility_validation_reports_missing_marker() -> None:
    result = validate_compatibility(
        required_markers=("python", "docker"),
        available_markers=("python",),
    )

    assert result.status is PhaseValidationStatus.FAIL
    assert result.evidence["missing_markers"] == "docker"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_release.py" @'
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationStatus,
)
from forge.domain_intelligence.phase_validation.release import (
    build_release_manifest,
    validate_release_readiness,
)


def test_release_readiness_passes() -> None:
    result = validate_release_readiness(
        branch="feature/m4.8",
        commit="abc1234",
        worktree_clean=True,
        require_clean_worktree=True,
        tag=None,
        require_release_tag=False,
    )

    assert result.status is PhaseValidationStatus.PASS


def test_release_readiness_requires_tag() -> None:
    result = validate_release_readiness(
        branch="main",
        commit="abc1234",
        worktree_clean=True,
        require_clean_worktree=True,
        tag=None,
        require_release_tag=True,
    )

    assert result.status is PhaseValidationStatus.FAIL


def test_release_manifest_is_deterministic() -> None:
    first = build_release_manifest(
        phase="4",
        milestone="M4.8",
        branch="main",
        commit="abc1234",
        tag="forge-v0.3-m4.8",
        validation_result_ids=("result-1",),
    )
    second = build_release_manifest(
        phase="4",
        milestone="M4.8",
        branch="main",
        commit="abc1234",
        tag="forge-v0.3-m4.8",
        validation_result_ids=("result-1",),
    )

    assert first.manifest_id == second.manifest_id
'@

Write-Utf8NoBom "tests\test_domain_intelligence_phase_validation_registry.py" @'
from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationKind,
)
from forge.domain_intelligence.phase_validation.registry import (
    PhaseValidationRegistry,
)


def test_default_phase_validation_registry() -> None:
    registry = PhaseValidationRegistry.default()

    assert {
        check.kind for check in registry.checks()
    } == {
        PhaseValidationKind.ACCEPTANCE,
        PhaseValidationKind.ARCHITECTURE,
        PhaseValidationKind.COMPATIBILITY,
        PhaseValidationKind.COVERAGE,
        PhaseValidationKind.RELEASE,
    }
'@

Write-Host ""
Write-Host "M4.8 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check . --fix
Assert-CommandSuccess "Ruff fix"

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_phase_validation_coverage.py `
    .\tests\test_domain_intelligence_phase_validation_compatibility.py `
    .\tests\test_domain_intelligence_phase_validation_release.py `
    .\tests\test_domain_intelligence_phase_validation_registry.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.8 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.8 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short