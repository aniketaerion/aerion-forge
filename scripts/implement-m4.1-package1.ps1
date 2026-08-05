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

Write-Utf8NoBom "forge\domain_intelligence\frontend\react.py" @'
"""React project detection for M4.1 Frontend Intelligence."""

from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from forge.domain_intelligence.errors import FrontendAnalysisError
from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
)


def load_package_json(project_root: Path) -> Mapping[str, Any]:
    """Load and validate package.json as a JSON object."""
    path = project_root / "package.json"

    if not path.is_file():
        return {}

    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FrontendAnalysisError(
            f"unable to read package.json: {path}"
        ) from exc

    if not isinstance(payload, dict):
        raise FrontendAnalysisError(
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


def detect_react(
    project_root: Path,
) -> tuple[FrontendFramework, ...]:
    """Detect React from package metadata and conventional sources."""
    package_json = load_package_json(project_root)
    dependencies = package_dependencies(package_json)

    detected = "react" in dependencies

    if not detected:
        candidates = (
            project_root / "src" / "main.jsx",
            project_root / "src" / "main.tsx",
            project_root / "src" / "App.jsx",
            project_root / "src" / "App.tsx",
        )
        detected = any(path.is_file() for path in candidates)

    return (FrontendFramework.REACT,) if detected else ()


def react_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce deterministic React discovery findings."""
    if not detect_react(project_root):
        return ()

    message = "React frontend framework detected."
    finding_id = frontend_finding_identifier(
        {
            "category": "framework",
            "framework": FrontendFramework.REACT.value,
            "root": project_root.as_posix(),
        }
    )

    return (
        FrontendFinding(
            finding_id=finding_id,
            category="framework",
            severity=FrontendFindingSeverity.INFO,
            message=message,
            path="package.json",
            evidence={"framework": FrontendFramework.REACT.value},
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\vite.py" @'
"""Vite project detection for M4.1 Frontend Intelligence."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.react import (
    load_package_json,
    package_dependencies,
)
from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
)


def detect_vite(
    project_root: Path,
) -> tuple[FrontendFramework, ...]:
    """Detect Vite from package metadata or configuration files."""
    package_json = load_package_json(project_root)
    dependencies = package_dependencies(package_json)

    config_names = (
        "vite.config.js",
        "vite.config.mjs",
        "vite.config.cjs",
        "vite.config.ts",
        "vite.config.mts",
        "vite.config.cts",
    )

    detected = (
        "vite" in dependencies
        or any((project_root / name).is_file() for name in config_names)
    )

    return (FrontendFramework.VITE,) if detected else ()


def vite_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce deterministic Vite discovery findings."""
    if not detect_vite(project_root):
        return ()

    finding_id = frontend_finding_identifier(
        {
            "category": "build_tool",
            "framework": FrontendFramework.VITE.value,
            "root": project_root.as_posix(),
        }
    )

    return (
        FrontendFinding(
            finding_id=finding_id,
            category="build_tool",
            severity=FrontendFindingSeverity.INFO,
            message="Vite build tooling detected.",
            path="package.json",
            evidence={"framework": FrontendFramework.VITE.value},
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\nextjs.py" @'
"""Next.js project detection for M4.1 Frontend Intelligence."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.react import (
    load_package_json,
    package_dependencies,
)
from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
    FrontendFramework,
)


def detect_nextjs(
    project_root: Path,
) -> tuple[FrontendFramework, ...]:
    """Detect Next.js from package metadata or configuration files."""
    package_json = load_package_json(project_root)
    dependencies = package_dependencies(package_json)

    config_names = (
        "next.config.js",
        "next.config.mjs",
        "next.config.ts",
    )

    detected = (
        "next" in dependencies
        or any((project_root / name).is_file() for name in config_names)
        or (project_root / "app").is_dir()
        or (project_root / "pages").is_dir()
    )

    return (FrontendFramework.NEXTJS,) if detected else ()


def nextjs_findings(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    """Produce deterministic Next.js discovery findings."""
    if not detect_nextjs(project_root):
        return ()

    finding_id = frontend_finding_identifier(
        {
            "category": "framework",
            "framework": FrontendFramework.NEXTJS.value,
            "root": project_root.as_posix(),
        }
    )

    return (
        FrontendFinding(
            finding_id=finding_id,
            category="framework",
            severity=FrontendFindingSeverity.INFO,
            message="Next.js frontend framework detected.",
            path="package.json",
            evidence={"framework": FrontendFramework.NEXTJS.value},
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\registry.py" @'
"""Analyzer registry for M4.1 Frontend Intelligence."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import Path

from forge.domain_intelligence.errors import (
    DomainIntelligenceConfigurationError,
)
from forge.domain_intelligence.models import FrontendFinding

FrontendAnalyzer = Callable[[Path], tuple[FrontendFinding, ...]]


class FrontendAnalyzerRegistry:
    """Deterministic registry of named frontend analyzers."""

    def __init__(
        self,
        analyzers: Iterable[
            tuple[str, FrontendAnalyzer]
        ] = (),
    ) -> None:
        self._analyzers: dict[str, FrontendAnalyzer] = {}

        for name, analyzer in analyzers:
            self.register(name, analyzer)

    def register(
        self,
        name: str,
        analyzer: FrontendAnalyzer,
    ) -> None:
        normalized = name.strip().lower()

        if not normalized:
            raise DomainIntelligenceConfigurationError(
                "frontend analyzer name cannot be empty"
            )

        if normalized in self._analyzers:
            raise DomainIntelligenceConfigurationError(
                f"duplicate frontend analyzer: {normalized}"
            )

        self._analyzers[normalized] = analyzer

    def get(self, name: str) -> FrontendAnalyzer:
        normalized = name.strip().lower()

        try:
            return self._analyzers[normalized]
        except KeyError as exc:
            raise DomainIntelligenceConfigurationError(
                f"frontend analyzer not registered: {normalized}"
            ) from exc

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._analyzers))

    def analyze(
        self,
        project_root: Path,
    ) -> tuple[FrontendFinding, ...]:
        findings: list[FrontendFinding] = []

        for name in self.names():
            findings.extend(self._analyzers[name](project_root))

        return tuple(
            sorted(
                findings,
                key=lambda finding: finding.finding_id,
            )
        )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\service.py" @'
"""Frontend project discovery service for M4.1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.nextjs import (
    detect_nextjs,
    nextjs_findings,
)
from forge.domain_intelligence.frontend.react import (
    detect_react,
    load_package_json,
    react_findings,
)
from forge.domain_intelligence.frontend.registry import (
    FrontendAnalyzerRegistry,
)
from forge.domain_intelligence.frontend.vite import (
    detect_vite,
    vite_findings,
)
from forge.domain_intelligence.identifiers import (
    frontend_project_identifier,
    frontend_report_identifier,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisReport,
    FrontendAnalysisRequest,
    FrontendFramework,
    FrontendProject,
)
from forge.domain_intelligence.policies import (
    DomainIntelligencePolicy,
    resolve_repository_root,
    validate_frontend_request,
)


def default_frontend_registry() -> FrontendAnalyzerRegistry:
    return FrontendAnalyzerRegistry(
        (
            ("nextjs", nextjs_findings),
            ("react", react_findings),
            ("vite", vite_findings),
        )
    )


class FrontendIntelligenceService:
    """Discover and classify frontend projects safely."""

    def __init__(
        self,
        policy: DomainIntelligencePolicy | None = None,
        registry: FrontendAnalyzerRegistry | None = None,
    ) -> None:
        self.policy = policy or DomainIntelligencePolicy()
        self.registry = registry or default_frontend_registry()

    def analyze(
        self,
        request: FrontendAnalysisRequest,
    ) -> FrontendAnalysisReport:
        validate_frontend_request(request, self.policy)

        repository_root = resolve_repository_root(
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
                "resolved frontend project root escaped repository"
            ) from exc

        package_json = load_package_json(project_root)
        frameworks = {
            *detect_react(project_root),
            *detect_vite(project_root),
            *detect_nextjs(project_root),
        }

        package_manager: str | None = None

        if (project_root / "pnpm-lock.yaml").is_file():
            package_manager = "pnpm"
        elif (project_root / "yarn.lock").is_file():
            package_manager = "yarn"
        elif (project_root / "package-lock.json").is_file():
            package_manager = "npm"
        elif "packageManager" in package_json:
            value = package_json["packageManager"]
            if isinstance(value, str):
                package_manager = value.split("@", maxsplit=1)[0]

        configuration_names = (
            "package.json",
            "vite.config.js",
            "vite.config.ts",
            "next.config.js",
            "next.config.mjs",
            "next.config.ts",
            "tsconfig.json",
            "jsconfig.json",
        )
        configuration_files = tuple(
            name
            for name in configuration_names
            if (project_root / name).is_file()
        )

        source_directories = tuple(
            name
            for name in ("src", "app", "pages", "components")
            if (project_root / name).is_dir()
        )

        project_payload = {
            "root": request.project_root,
            "frameworks": sorted(
                framework.value for framework in frameworks
            ),
            "package_manager": package_manager,
        }

        project = FrontendProject(
            project_id=frontend_project_identifier(project_payload),
            root=request.project_root,
            frameworks=tuple(
                sorted(
                    frameworks,
                    key=lambda framework: framework.value,
                )
            )
            or (FrontendFramework.UNKNOWN,),
            package_manager=package_manager,
            source_directories=source_directories,
            configuration_files=configuration_files,
        )

        findings = self.registry.analyze(project_root)

        return FrontendAnalysisReport(
            report_id=frontend_report_identifier(
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

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_react.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.frontend.react import (
    detect_react,
    load_package_json,
    package_dependencies,
)
from forge.domain_intelligence.models import FrontendFramework


def write_package_json(
    root: Path,
    payload: dict[str, object],
) -> None:
    (root / "package.json").write_text(
        json.dumps(payload),
        encoding="utf-8",
    )


def test_detect_react_from_dependency(tmp_path: Path) -> None:
    write_package_json(
        tmp_path,
        {"dependencies": {"react": "^19.0.0"}},
    )

    assert detect_react(tmp_path) == (
        FrontendFramework.REACT,
    )


def test_package_dependencies_merges_sections(
    tmp_path: Path,
) -> None:
    write_package_json(
        tmp_path,
        {
            "dependencies": {"react": "^19.0.0"},
            "devDependencies": {"vite": "^7.0.0"},
        },
    )

    dependencies = package_dependencies(
        load_package_json(tmp_path)
    )

    assert dependencies == {
        "react": "^19.0.0",
        "vite": "^7.0.0",
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_vite.py" @'
from pathlib import Path

from forge.domain_intelligence.frontend.vite import detect_vite
from forge.domain_intelligence.models import FrontendFramework


def test_detect_vite_from_configuration(tmp_path: Path) -> None:
    (tmp_path / "vite.config.ts").write_text(
        "export default {}",
        encoding="utf-8",
    )

    assert detect_vite(tmp_path) == (
        FrontendFramework.VITE,
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_nextjs.py" @'
from pathlib import Path

from forge.domain_intelligence.frontend.nextjs import detect_nextjs
from forge.domain_intelligence.models import FrontendFramework


def test_detect_nextjs_from_app_directory(tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()

    assert detect_nextjs(tmp_path) == (
        FrontendFramework.NEXTJS,
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_registry.py" @'
from pathlib import Path

import pytest

from forge.domain_intelligence.errors import (
    DomainIntelligenceConfigurationError,
)
from forge.domain_intelligence.frontend.registry import (
    FrontendAnalyzerRegistry,
)
from forge.domain_intelligence.models import FrontendFinding


def empty_analyzer(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    del project_root
    return ()


def test_registry_names_are_deterministic() -> None:
    registry = FrontendAnalyzerRegistry(
        (
            ("vite", empty_analyzer),
            ("react", empty_analyzer),
        )
    )

    assert registry.names() == ("react", "vite")


def test_registry_rejects_duplicate_name() -> None:
    with pytest.raises(DomainIntelligenceConfigurationError):
        FrontendAnalyzerRegistry(
            (
                ("react", empty_analyzer),
                ("REACT", empty_analyzer),
            )
        )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_service.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.frontend.service import (
    FrontendIntelligenceService,
)
from forge.domain_intelligence.models import (
    FrontendAnalysisRequest,
    FrontendFramework,
)


def initialize_repository(tmp_path: Path) -> None:
    (tmp_path / ".git").mkdir()


def test_service_discovers_react_vite_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)
    (tmp_path / "src").mkdir()
    (tmp_path / "package-lock.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {"react": "^19.0.0"},
                "devDependencies": {"vite": "^7.0.0"},
            }
        ),
        encoding="utf-8",
    )

    report = FrontendIntelligenceService().analyze(
        FrontendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.frameworks == (
        FrontendFramework.REACT,
        FrontendFramework.VITE,
    )
    assert report.project.package_manager == "npm"
    assert len(report.findings) == 2


def test_service_reports_unknown_project(
    tmp_path: Path,
) -> None:
    initialize_repository(tmp_path)

    report = FrontendIntelligenceService().analyze(
        FrontendAnalysisRequest(
            repository_root=str(tmp_path),
        )
    )

    assert report.project.frameworks == (
        FrontendFramework.UNKNOWN,
    )
    assert not report.findings
'@

Write-Host ""
Write-Host "M4.1 Package 1 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_frontend_react.py `
    .\tests\test_domain_intelligence_frontend_vite.py `
    .\tests\test_domain_intelligence_frontend_nextjs.py `
    .\tests\test_domain_intelligence_frontend_registry.py `
    .\tests\test_domain_intelligence_frontend_service.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.1 Package 1 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.1 PACKAGE 1 COMPLETE" -ForegroundColor Green

git status --short