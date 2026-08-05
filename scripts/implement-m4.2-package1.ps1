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

Write-Utf8NoBom "forge\domain_intelligence\backend\node.py" @'
"""Node.js backend discovery for M4.2 Backend Intelligence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.domain_intelligence.backend.errors import BackendManifestError
from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendRuntime,
)


def load_package_json(project_root: Path) -> Mapping[str, Any]:
    """Load package.json without executing project code."""
    path = project_root / "package.json"

    if not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BackendManifestError(
            f"unable to read package.json: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise BackendManifestError(
            f"package.json must contain an object: {path}"
        )

    return payload


def package_dependencies(
    package_json: Mapping[str, Any],
) -> dict[str, str]:
    """Return normalized runtime and development dependencies."""
    dependencies: dict[str, str] = {}

    for section in ("dependencies", "devDependencies"):
        values = package_json.get(section, {})

        if not isinstance(values, dict):
            continue

        for name, version in values.items():
            if isinstance(name, str) and isinstance(version, str):
                dependencies[name] = version

    return dependencies


def detect_node_runtime(
    project_root: Path,
) -> tuple[BackendRuntime, ...]:
    """Detect a Node.js backend runtime."""
    package_json = load_package_json(project_root)

    detected = bool(package_json) or any(
        (project_root / name).is_file()
        for name in (
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
        )
    )

    return (BackendRuntime.NODEJS,) if detected else ()


def detect_node_frameworks(
    project_root: Path,
) -> tuple[BackendFramework, ...]:
    """Detect Node.js backend frameworks."""
    dependencies = package_dependencies(
        load_package_json(project_root)
    )

    frameworks: set[BackendFramework] = set()

    if detect_node_runtime(project_root):
        frameworks.add(BackendFramework.NODE)

    if "express" in dependencies:
        frameworks.add(BackendFramework.EXPRESS)

    if "@nestjs/core" in dependencies:
        frameworks.add(BackendFramework.NESTJS)

    return tuple(
        sorted(frameworks, key=lambda framework: framework.value)
    )


def node_findings(project_root: Path) -> tuple[BackendFinding, ...]:
    """Produce deterministic Node.js discovery findings."""
    findings: list[BackendFinding] = []

    for framework in detect_node_frameworks(project_root):
        finding_id = backend_finding_identifier(
            {
                "category": "framework",
                "framework": framework.value,
                "root": project_root.as_posix(),
            }
        )

        findings.append(
            BackendFinding(
                finding_id=finding_id,
                category="framework",
                severity=BackendFindingSeverity.INFO,
                message=f"Backend framework detected: {framework.value}",
                path="package.json",
                evidence={
                    "framework": framework.value,
                    "runtime": BackendRuntime.NODEJS.value,
                },
            )
        )

    return tuple(findings)
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\fastapi.py" @'
"""FastAPI backend discovery for M4.2 Backend Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendRuntime,
)

_FASTAPI_PATTERN = re.compile(
    r"(?:from\s+fastapi\s+import|import\s+fastapi|FastAPI\s*\()"
)


def detect_fastapi(
    project_root: Path,
) -> tuple[BackendFramework, ...]:
    """Detect FastAPI from manifests or source files."""
    manifest_names = (
        "requirements.txt",
        "pyproject.toml",
        "Pipfile",
        "poetry.lock",
    )

    for name in manifest_names:
        path = project_root / name
        if not path.is_file():
            continue

        try:
            if "fastapi" in path.read_text(
                encoding="utf-8-sig"
            ).lower():
                return (BackendFramework.FASTAPI,)
        except OSError:
            continue

    for path in project_root.rglob("*.py"):
        if any(
            excluded in path.parts
            for excluded in (
                ".venv",
                "venv",
                "__pycache__",
                ".git",
            )
        ):
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if _FASTAPI_PATTERN.search(source):
            return (BackendFramework.FASTAPI,)

    return ()


def fastapi_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce deterministic FastAPI discovery findings."""
    if not detect_fastapi(project_root):
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "framework",
            "framework": BackendFramework.FASTAPI.value,
            "root": project_root.as_posix(),
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="framework",
            severity=BackendFindingSeverity.INFO,
            message="Backend framework detected: fastapi",
            evidence={
                "framework": BackendFramework.FASTAPI.value,
                "runtime": BackendRuntime.PYTHON.value,
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\django.py" @'
"""Django backend discovery for M4.2 Backend Intelligence."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
    BackendFramework,
    BackendRuntime,
)


def detect_django(
    project_root: Path,
) -> tuple[BackendFramework, ...]:
    """Detect Django from manifests and conventional files."""
    if (project_root / "manage.py").is_file():
        return (BackendFramework.DJANGO,)

    manifest_names = (
        "requirements.txt",
        "pyproject.toml",
        "Pipfile",
        "poetry.lock",
    )

    for name in manifest_names:
        path = project_root / name
        if not path.is_file():
            continue

        try:
            if "django" in path.read_text(
                encoding="utf-8-sig"
            ).lower():
                return (BackendFramework.DJANGO,)
        except OSError:
            continue

    for path in project_root.rglob("settings.py"):
        if any(
            excluded in path.parts
            for excluded in (
                ".venv",
                "venv",
                "__pycache__",
                ".git",
            )
        ):
            continue
        return (BackendFramework.DJANGO,)

    return ()


def django_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce deterministic Django discovery findings."""
    if not detect_django(project_root):
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "framework",
            "framework": BackendFramework.DJANGO.value,
            "root": project_root.as_posix(),
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="framework",
            severity=BackendFindingSeverity.INFO,
            message="Backend framework detected: django",
            path="manage.py",
            evidence={
                "framework": BackendFramework.DJANGO.value,
                "runtime": BackendRuntime.PYTHON.value,
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\registry.py" @'
"""Analyzer registry for M4.2 Backend Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.backend.errors import (
    BackendConfigurationError,
)
from forge.domain_intelligence.backend.models import BackendFinding

BackendAnalyzer = Callable[[Path], tuple[BackendFinding, ...]]


class BackendAnalyzerRegistry:
    """Deterministic registry of named backend analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, BackendAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, BackendAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: BackendAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise BackendConfigurationError(
                "backend analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise BackendConfigurationError(
                f"duplicate backend analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[BackendFinding, ...]:
        findings: list[BackendFinding] = []

        for name in self.names():
            findings.extend(
                self._analyzers[name](project_root)
            )

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\service.py" @'
"""Backend discovery service for M4.2."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.backend.django import (
    detect_django,
    django_findings,
)
from forge.domain_intelligence.backend.fastapi import (
    detect_fastapi,
    fastapi_findings,
)
from forge.domain_intelligence.backend.identifiers import (
    backend_project_identifier,
    backend_report_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendAnalysisReport,
    BackendAnalysisRequest,
    BackendFramework,
    BackendProject,
    BackendRuntime,
)
from forge.domain_intelligence.backend.node import (
    detect_node_frameworks,
    detect_node_runtime,
    load_package_json,
    node_findings,
)
from forge.domain_intelligence.backend.policies import (
    BackendIntelligencePolicy,
    resolve_backend_repository_root,
    validate_backend_request,
)
from forge.domain_intelligence.backend.registry import (
    BackendAnalyzerRegistry,
)


def default_backend_registry() -> BackendAnalyzerRegistry:
    """Return the M4.2 Package 1 analyzer registry."""
    return BackendAnalyzerRegistry(
        (
            ("django", django_findings),
            ("fastapi", fastapi_findings),
            ("node", node_findings),
        )
    )


class BackendIntelligenceService:
    """Discover backend runtime and framework metadata safely."""

    def __init__(
        self,
        policy: BackendIntelligencePolicy | None = None,
        registry: BackendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or BackendIntelligencePolicy()
        self.registry = registry or default_backend_registry()

    def analyze(
        self,
        request: BackendAnalysisRequest,
    ) -> BackendAnalysisReport:
        """Run backend framework discovery."""
        validate_backend_request(request, self.policy)

        repository_root = resolve_backend_repository_root(
            request.repository_root,
            self.policy,
        )
        project_root = (
            repository_root / request.project_root
        ).resolve()

        try:
            project_root.relative_to(repository_root)
        except ValueError as exc:
            raise ValueError(
                "resolved backend project root escaped repository"
            ) from exc

        runtimes: set[BackendRuntime] = set(
            detect_node_runtime(project_root)
        )
        frameworks: set[BackendFramework] = set(
            detect_node_frameworks(project_root)
        )

        if detect_fastapi(project_root):
            runtimes.add(BackendRuntime.PYTHON)
            frameworks.add(BackendFramework.FASTAPI)

        if detect_django(project_root):
            runtimes.add(BackendRuntime.PYTHON)
            frameworks.add(BackendFramework.DJANGO)

        package_manager: str | None = None

        if (project_root / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif (project_root / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (project_root / "package-lock.json").is_file():
            package_manager = "npm"
        elif (project_root / "poetry.lock").is_file():
            package_manager = "poetry"
        elif (project_root / "Pipfile").is_file():
            package_manager = "pipenv"
        elif (project_root / "requirements.txt").is_file():
            package_manager = "pip"

        package_json = load_package_json(project_root)

        if (
            package_manager is None
            and isinstance(
                package_json.get("packageManager"),
                str,
            )
        ):
            value = str(package_json["packageManager"])
            package_manager = value.split("@", maxsplit=1)[0]

        configuration_names = (
            "package.json",
            "package-lock.json",
            "pnpm-lock.yaml",
            "yarn.lock",
            "requirements.txt",
            "pyproject.toml",
            "Pipfile",
            "poetry.lock",
            "manage.py",
        )
        configuration_files = tuple(
            name
            for name in configuration_names
            if (project_root / name).is_file()
        )

        source_directories = tuple(
            name
            for name in (
                "src",
                "app",
                "apps",
                "server",
                "api",
                "backend",
            )
            if (project_root / name).is_dir()
        )

        findings = self.registry.analyze(project_root)

        project_payload = {
            "root": request.project_root,
            "runtimes": sorted(
                runtime.value for runtime in runtimes
            ),
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
        }

        project = BackendProject(
            project_id=backend_project_identifier(
                project_payload
            ),
            root=request.project_root,
            runtimes=tuple(
                sorted(
                    runtimes,
                    key=lambda runtime: runtime.value,
                )
            )
            or (BackendRuntime.UNKNOWN,),
            frameworks=tuple(
                sorted(
                    frameworks,
                    key=lambda framework: framework.value,
                )
            )
            or (BackendFramework.UNKNOWN,),
            package_manager=package_manager,
            source_directories=source_directories,
            configuration_files=configuration_files,
        )

        return BackendAnalysisReport(
            report_id=backend_report_identifier(
                {
                    "project_id": project.project_id,
                    "finding_ids": [
                        finding.finding_id
                        for finding in findings
                    ],
                }
            ),
            project=project,
            findings=findings,
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_node.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.backend.models import (
    BackendFramework,
    BackendRuntime,
)
from forge.domain_intelligence.backend.node import (
    detect_node_frameworks,
    detect_node_runtime,
)


def test_detect_node_express_project(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    assert detect_node_runtime(tmp_path) == (
        BackendRuntime.NODEJS,
    )
    assert detect_node_frameworks(tmp_path) == (
        BackendFramework.EXPRESS,
        BackendFramework.NODE,
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_fastapi.py" @'
from pathlib import Path

from forge.domain_intelligence.backend.fastapi import detect_fastapi
from forge.domain_intelligence.backend.models import BackendFramework


def test_detect_fastapi_from_requirements(tmp_path: Path) -> None:
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\nuvicorn==0.35.0\n",
        encoding="utf-8",
    )

    assert detect_fastapi(tmp_path) == (
        BackendFramework.FASTAPI,
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_django.py" @'
from pathlib import Path

from forge.domain_intelligence.backend.django import detect_django
from forge.domain_intelligence.backend.models import BackendFramework


def test_detect_django_from_manage_py(tmp_path: Path) -> None:
    (tmp_path / "manage.py").write_text(
        "from django.core.management import execute_from_command_line",
        encoding="utf-8",
    )

    assert detect_django(tmp_path) == (
        BackendFramework.DJANGO,
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_registry.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.backend.errors import (
    BackendConfigurationError,
)
from forge.domain_intelligence.backend.models import BackendFinding
from forge.domain_intelligence.backend.registry import (
    BackendAnalyzerRegistry,
)


def empty_analyzer(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    del project_root
    return ()


def test_backend_registry_names_are_sorted() -> None:
    registry = BackendAnalyzerRegistry(
        (
            ("node", empty_analyzer),
            ("django", empty_analyzer),
        )
    )

    assert registry.names() == ("django", "node")


def test_backend_registry_rejects_duplicates() -> None:
    with pytest.raises(BackendConfigurationError):
        BackendAnalyzerRegistry(
            (
                ("node", empty_analyzer),
                ("NODE", empty_analyzer),
            )
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_service.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.backend.models import (
    BackendAnalysisRequest,
    BackendFramework,
    BackendRuntime,
)
from forge.domain_intelligence.backend.service import (
    BackendIntelligenceService,
    default_backend_registry,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_default_backend_registry() -> None:
    assert default_backend_registry().names() == (
        "django",
        "fastapi",
        "node",
    )


def test_service_discovers_node_and_fastapi(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "express": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\n",
        encoding="utf-8",
    )

    report = BackendIntelligenceService().analyze(
        BackendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.runtimes == (
        BackendRuntime.NODEJS,
        BackendRuntime.PYTHON,
    )
    assert report.project.frameworks == (
        BackendFramework.EXPRESS,
        BackendFramework.FASTAPI,
        BackendFramework.NODE,
    )
    assert report.project.package_manager == "npm"


def test_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = BackendIntelligenceService().analyze(
        BackendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.runtimes == (
        BackendRuntime.UNKNOWN,
    )
    assert report.project.frameworks == (
        BackendFramework.UNKNOWN,
    )
    assert not report.findings
'@

Write-Host ""
Write-Host "M4.2 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_backend_node.py `
    .\tests\test_domain_intelligence_backend_fastapi.py `
    .\tests\test_domain_intelligence_backend_django.py `
    .\tests\test_domain_intelligence_backend_registry.py `
    .\tests\test_domain_intelligence_backend_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.2 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.2 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short
