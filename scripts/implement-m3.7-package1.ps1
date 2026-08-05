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

Write-Utf8NoBom "forge\build_verification\providers\base.py" @'
"""Provider contracts for M3.7 Build Verification."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)


class BuildVerificationProvider(ABC):
    """Base class for registered build-verification providers."""

    tool: VerificationTool

    @abstractmethod
    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        """Return a bounded argv tuple for one verification step."""

    def supports(self, tool: VerificationTool) -> bool:
        """Return whether this provider supports the requested tool."""
        return tool is self.tool
'@

Write-Utf8NoBom "forge\build_verification\providers\python.py" @'
"""Python build-verification providers."""

from __future__ import annotations

import sys
from pathlib import Path

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.base import BuildVerificationProvider


class RuffProvider(BuildVerificationProvider):
    """Run Ruff through the active Python interpreter."""

    tool = VerificationTool.RUFF

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root, policy
        return (sys.executable, "-m", "ruff", "check", *step.arguments)


class MyPyProvider(BuildVerificationProvider):
    """Run MyPy through the active Python interpreter."""

    tool = VerificationTool.MYPY

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root, policy
        return (sys.executable, "-m", "mypy", *step.arguments)


class PytestProvider(BuildVerificationProvider):
    """Run pytest through the active Python interpreter."""

    tool = VerificationTool.PYTEST

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root, policy
        return (
            sys.executable,
            "-m",
            "pytest",
            "-p",
            "no:cacheprovider",
            *step.arguments,
        )


class PythonBuildProvider(BuildVerificationProvider):
    """Run `python -m build` without network access."""

    tool = VerificationTool.PYTHON_BUILD

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        del repository_root

        if step.allow_network or policy.allow_network:
            raise BuildVerificationProviderError(
                "Python build verification must remain offline"
            )

        return (
            sys.executable,
            "-m",
            "build",
            "--no-isolation",
            *step.arguments,
        )
'@

Write-Utf8NoBom "forge\build_verification\providers\node.py" @'
"""Node build-verification providers."""

from __future__ import annotations

from pathlib import Path

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.base import BuildVerificationProvider


class _NodeScriptProvider(BuildVerificationProvider):
    script_name: str

    def command(
        self,
        step: VerificationStep,
        repository_root: Path,
        policy: BuildVerificationPolicy,
    ) -> tuple[str, ...]:
        package_json = repository_root / step.working_directory / "package.json"

        if not package_json.is_file():
            raise BuildVerificationProviderError(
                f"package.json not found for step: {step.step_id}"
            )

        if step.allow_network or policy.allow_network:
            raise BuildVerificationProviderError(
                "Node build verification must remain offline"
            )

        return (
            "npm",
            "run",
            self.script_name,
            "--",
            *step.arguments,
        )


class NodeLintProvider(_NodeScriptProvider):
    """Run the repository's Node lint script."""

    tool = VerificationTool.NODE_LINT
    script_name = "lint"


class NodeTestProvider(_NodeScriptProvider):
    """Run the repository's Node test script."""

    tool = VerificationTool.NODE_TEST
    script_name = "test"


class NodeBuildProvider(_NodeScriptProvider):
    """Run the repository's Node build script."""

    tool = VerificationTool.NODE_BUILD
    script_name = "build"
'@

Write-Utf8NoBom "forge\build_verification\providers\__init__.py" @'
"""Registered M3.7 build-verification providers."""

from forge.build_verification.providers.base import BuildVerificationProvider
from forge.build_verification.providers.node import (
    NodeBuildProvider,
    NodeLintProvider,
    NodeTestProvider,
)
from forge.build_verification.providers.python import (
    MyPyProvider,
    PytestProvider,
    PythonBuildProvider,
    RuffProvider,
)

__all__ = [
    "BuildVerificationProvider",
    "MyPyProvider",
    "NodeBuildProvider",
    "NodeLintProvider",
    "NodeTestProvider",
    "PytestProvider",
    "PythonBuildProvider",
    "RuffProvider",
]
'@

Write-Utf8NoBom "forge\build_verification\registry.py" @'
"""Provider registry for M3.7 Build Verification."""

from __future__ import annotations

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import VerificationTool
from forge.build_verification.providers import (
    BuildVerificationProvider,
    MyPyProvider,
    NodeBuildProvider,
    NodeLintProvider,
    NodeTestProvider,
    PytestProvider,
    PythonBuildProvider,
    RuffProvider,
)


class BuildVerificationProviderRegistry:
    """Deterministic registry keyed by verification tool."""

    def __init__(
        self,
        providers: tuple[BuildVerificationProvider, ...] | None = None,
    ) -> None:
        selected = providers or (
            RuffProvider(),
            MyPyProvider(),
            PytestProvider(),
            PythonBuildProvider(),
            NodeLintProvider(),
            NodeTestProvider(),
            NodeBuildProvider(),
        )

        self._providers = {
            provider.tool: provider
            for provider in selected
        }

        if len(self._providers) != len(selected):
            raise BuildVerificationProviderError(
                "duplicate build verification provider registration"
            )

    def get(
        self,
        tool: VerificationTool,
    ) -> BuildVerificationProvider:
        """Return the provider for one verification tool."""
        try:
            return self._providers[tool]
        except KeyError as exc:
            raise BuildVerificationProviderError(
                f"no provider registered for tool: {tool.value}"
            ) from exc

    def tools(self) -> tuple[VerificationTool, ...]:
        """Return registered tools in deterministic order."""
        return tuple(sorted(self._providers, key=lambda item: item.value))
'@

Write-Utf8NoBom "forge\build_verification\runner.py" @'
"""Bounded subprocess runner for M3.7 Build Verification."""

from __future__ import annotations

import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic

from forge.build_verification.errors import (
    BuildVerificationProviderError,
)
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
)
from forge.build_verification.registry import (
    BuildVerificationProviderRegistry,
)


def _bounded_lines(
    text: str,
    limit: int,
) -> tuple[str, ...]:
    lines = text.splitlines()

    if len(lines) <= limit:
        return tuple(lines)

    return (
        *lines[:limit],
        f"... truncated {len(lines) - limit} lines ...",
    )


def run_step(
    repository_root: Path,
    step: VerificationStep,
    policy: BuildVerificationPolicy,
    registry: BuildVerificationProviderRegistry | None = None,
) -> VerificationStepResult:
    """Execute exactly one registered verification step."""
    root = repository_root.resolve()
    working_directory = (root / step.working_directory).resolve()

    try:
        working_directory.relative_to(root)
    except ValueError as exc:
        raise BuildVerificationProviderError(
            f"step working directory escapes repository: {step.step_id}"
        ) from exc

    if not working_directory.is_dir():
        raise BuildVerificationProviderError(
            f"step working directory does not exist: {step.step_id}"
        )

    selected_registry = registry or BuildVerificationProviderRegistry()
    provider = selected_registry.get(step.tool)
    command = provider.command(step, root, policy)

    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PIP_DISABLE_PIP_VERSION_CHECK"] = "1"
    environment["NO_COLOR"] = "1"

    started_at = datetime.now(UTC)
    started = monotonic()

    try:
        completed = subprocess.run(
            command,
            cwd=working_directory,
            env=environment,
            capture_output=True,
            text=True,
            timeout=step.timeout_seconds,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        duration = monotonic() - started
        stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else exc.stdout
        stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else exc.stderr

        return VerificationStepResult(
            step_id=step.step_id,
            status=VerificationStatus.TIMED_OUT,
            exit_code=None,
            duration_seconds=duration,
            stdout=_bounded_lines(
                stdout or "",
                policy.max_output_lines,
            ),
            stderr=_bounded_lines(
                stderr or "",
                policy.max_output_lines,
            ),
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
    except OSError as exc:
        raise BuildVerificationProviderError(
            f"unable to execute verification step {step.step_id}: {exc}"
        ) from exc

    duration = monotonic() - started
    status = (
        VerificationStatus.PASSED
        if completed.returncode == 0
        else VerificationStatus.FAILED
    )

    return VerificationStepResult(
        step_id=step.step_id,
        status=status,
        exit_code=completed.returncode,
        duration_seconds=duration,
        stdout=_bounded_lines(
            completed.stdout,
            policy.max_output_lines,
        ),
        stderr=_bounded_lines(
            completed.stderr,
            policy.max_output_lines,
        ),
        started_at=started_at,
        completed_at=datetime.now(UTC),
    )
'@

Write-Utf8NoBom "tests\test_build_verification_registry.py" @'
import pytest

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import VerificationTool
from forge.build_verification.providers.base import BuildVerificationProvider
from forge.build_verification.registry import (
    BuildVerificationProviderRegistry,
)


class DuplicateProvider(BuildVerificationProvider):
    tool = VerificationTool.RUFF

    def command(self, step, repository_root, policy):
        del step, repository_root, policy
        return ("python",)


def test_registry_returns_registered_provider() -> None:
    registry = BuildVerificationProviderRegistry()

    assert registry.get(VerificationTool.RUFF).tool is VerificationTool.RUFF


def test_registry_tools_are_sorted() -> None:
    registry = BuildVerificationProviderRegistry()
    values = tuple(tool.value for tool in registry.tools())

    assert values == tuple(sorted(values))


def test_registry_rejects_duplicate_tools() -> None:
    with pytest.raises(BuildVerificationProviderError):
        BuildVerificationProviderRegistry(
            (DuplicateProvider(), DuplicateProvider())
        )
'@

Write-Utf8NoBom "tests\test_build_verification_python_provider.py" @'
import sys
from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.python import (
    PytestProvider,
    PythonBuildProvider,
    RuffProvider,
)


def test_ruff_provider_uses_active_python(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="ruff",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=(".",),
    )

    command = RuffProvider().command(
        step,
        tmp_path,
        BuildVerificationPolicy(),
    )

    assert command[:4] == (sys.executable, "-m", "ruff", "check")


def test_pytest_provider_disables_cache_provider(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="pytest",
        tool=VerificationTool.PYTEST,
        name="Pytest",
    )

    command = PytestProvider().command(
        step,
        tmp_path,
        BuildVerificationPolicy(),
    )

    assert ("-p", "no:cacheprovider") == command[3:5]


def test_python_build_provider_rejects_network(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="build",
        tool=VerificationTool.PYTHON_BUILD,
        name="Build",
        allow_network=True,
    )

    with pytest.raises(BuildVerificationProviderError):
        PythonBuildProvider().command(
            step,
            tmp_path,
            BuildVerificationPolicy(allow_network=True),
        )
'@

Write-Utf8NoBom "tests\test_build_verification_node_provider.py" @'
from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.providers.node import (
    NodeBuildProvider,
    NodeLintProvider,
)


def test_node_lint_provider_builds_npm_command(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text("{}", encoding="utf-8")
    step = VerificationStep(
        step_id="lint",
        tool=VerificationTool.NODE_LINT,
        name="Node lint",
        arguments=("--silent",),
    )

    command = NodeLintProvider().command(
        step,
        tmp_path,
        BuildVerificationPolicy(),
    )

    assert command == ("npm", "run", "lint", "--", "--silent")


def test_node_provider_requires_package_json(tmp_path: Path) -> None:
    step = VerificationStep(
        step_id="build",
        tool=VerificationTool.NODE_BUILD,
        name="Node build",
    )

    with pytest.raises(BuildVerificationProviderError):
        NodeBuildProvider().command(
            step,
            tmp_path,
            BuildVerificationPolicy(),
        )
'@

Write-Utf8NoBom "tests\test_build_verification_runner.py" @'
from pathlib import Path

from forge.build_verification.models import (
    BuildVerificationPolicy,
    VerificationStatus,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.runner import run_step


def test_runner_executes_passing_ruff_step(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("value = 1\n", encoding="utf-8")

    step = VerificationStep(
        step_id="ruff-pass",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
        timeout_seconds=30,
    )

    result = run_step(
        tmp_path,
        step,
        BuildVerificationPolicy(),
    )

    assert result.status is VerificationStatus.PASSED
    assert result.exit_code == 0


def test_runner_captures_failed_ruff_step(tmp_path: Path) -> None:
    source = tmp_path / "sample.py"
    source.write_text("import os\n", encoding="utf-8")

    step = VerificationStep(
        step_id="ruff-fail",
        tool=VerificationTool.RUFF,
        name="Ruff",
        arguments=("sample.py",),
        timeout_seconds=30,
    )

    result = run_step(
        tmp_path,
        step,
        BuildVerificationPolicy(),
    )

    assert result.status is VerificationStatus.FAILED
    assert result.exit_code != 0
    assert any("F401" in line for line in result.stdout)
'@

Write-Host ""
Write-Host "M3.7 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_build_verification_registry.py `
    .\tests\test_build_verification_python_provider.py `
    .\tests\test_build_verification_node_provider.py `
    .\tests\test_build_verification_runner.py `
    -p no:cacheprovider
Assert-CommandSuccess "M3.7 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M3.7 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
