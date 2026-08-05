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

Write-Utf8NoBom "forge\domain_intelligence\backend\dependencies.py" @'
"""Backend dependency analysis for M4.2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)
from forge.domain_intelligence.backend.node import (
    load_package_json,
    package_dependencies,
)

_REQUIREMENT_PATTERN = re.compile(
    r"^\s*([A-Za-z0-9_.-]+)"
)


def python_dependencies(
    project_root: Path,
) -> dict[str, str]:
    """Read direct Python dependencies without resolving packages."""
    dependencies: dict[str, str] = {}

    requirements = project_root / "requirements.txt"
    if requirements.is_file():
        try:
            lines = requirements.read_text(
                encoding="utf-8-sig"
            ).splitlines()
        except OSError:
            lines = []

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            match = _REQUIREMENT_PATTERN.match(stripped)
            if match is not None:
                dependencies[match.group(1).lower()] = stripped

    pyproject = project_root / "pyproject.toml"
    if pyproject.is_file():
        try:
            content = pyproject.read_text(
                encoding="utf-8-sig"
            )
        except OSError:
            content = ""

        for name in (
            "fastapi",
            "django",
            "flask",
            "sqlalchemy",
            "celery",
            "redis",
            "uvicorn",
            "gunicorn",
        ):
            if re.search(
                rf"(?im)^[^#\r\n]*\b{re.escape(name)}\b",
                content,
            ):
                dependencies.setdefault(name, "pyproject.toml")

    return dict(sorted(dependencies.items()))


def node_dependencies(
    project_root: Path,
) -> dict[str, str]:
    """Return direct Node.js dependencies."""
    return dict(
        sorted(
            package_dependencies(
                load_package_json(project_root)
            ).items()
        )
    )


def dependency_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce findings summarizing backend dependencies."""
    findings: list[BackendFinding] = []

    dependency_sets = {
        "node": node_dependencies(project_root),
        "python": python_dependencies(project_root),
    }

    for runtime, dependencies in dependency_sets.items():
        if not dependencies:
            continue

        finding_id = backend_finding_identifier(
            {
                "category": "dependencies",
                "runtime": runtime,
                "dependencies": dependencies,
            }
        )

        findings.append(
            BackendFinding(
                finding_id=finding_id,
                category="dependencies",
                severity=BackendFindingSeverity.INFO,
                message=(
                    f"{runtime} backend dependencies detected."
                ),
                evidence={
                    "runtime": runtime,
                    "dependency_count": str(len(dependencies)),
                    "dependencies": ",".join(dependencies),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\configuration.py" @'
"""Backend configuration discovery for M4.2."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)

_CONFIGURATION_NAMES = (
    "package.json",
    "tsconfig.json",
    "nest-cli.json",
    "requirements.txt",
    "pyproject.toml",
    "Pipfile",
    "poetry.lock",
    "manage.py",
    "alembic.ini",
    "gunicorn.conf.py",
    "docker-compose.yml",
    "docker-compose.yaml",
    "Dockerfile",
)

_SECRET_NAMES = {
    ".env",
    ".env.local",
    ".env.production",
    ".env.development",
}


def discover_configuration_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover safe backend configuration file names."""
    discovered = {
        name
        for name in _CONFIGURATION_NAMES
        if (project_root / name).is_file()
    }

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
            )
        ):
            continue

        if path.name in _SECRET_NAMES:
            continue

        if path.name in _CONFIGURATION_NAMES:
            discovered.add(
                path.relative_to(project_root).as_posix()
            )

    return tuple(sorted(discovered))


def configuration_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a configuration inventory finding."""
    files = discover_configuration_files(project_root)

    if not files:
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "configuration",
            "files": files,
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="configuration",
            severity=BackendFindingSeverity.INFO,
            message="Backend configuration files detected.",
            evidence={
                "file_count": str(len(files)),
                "files": ",".join(files),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\services.py" @'
"""Backend service topology discovery for M4.2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)

_SERVICE_NAME_PATTERN = re.compile(
    r"(?:^|[_\-.])(service|controller|router|handler|repository)(?:[_\-.]|$)",
    re.IGNORECASE,
)


def discover_service_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover likely backend service-layer files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".js",
            ".mjs",
            ".cjs",
            ".ts",
            ".py",
        }:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        stem = path.stem.lower()
        parent_names = {
            part.lower() for part in path.parent.parts
        }

        if (
            _SERVICE_NAME_PATTERN.search(path.name)
            or stem in {
                "app",
                "main",
                "server",
                "api",
                "routes",
                "urls",
                "views",
            }
            or parent_names.intersection(
                {
                    "services",
                    "controllers",
                    "routers",
                    "handlers",
                    "repositories",
                }
            )
        ):
            files.add(
                path.relative_to(project_root).as_posix()
            )

    return tuple(sorted(files))


def service_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a backend service-topology finding."""
    files = discover_service_files(project_root)

    if not files:
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "services",
            "files": files,
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="services",
            severity=BackendFindingSeverity.INFO,
            message="Backend service-layer files detected.",
            evidence={
                "service_file_count": str(len(files)),
                "service_files": ",".join(files),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\workers.py" @'
"""Backend worker and scheduled-job discovery for M4.2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)

_WORKER_PATTERN = re.compile(
    r"\b(celery|bullmq|bull|rq|dramatiq|apscheduler|cron|worker_threads)\b",
    re.IGNORECASE,
)


def discover_worker_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover likely worker, queue, and scheduled-job files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".js",
            ".mjs",
            ".cjs",
            ".ts",
            ".py",
        }:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        relative = path.relative_to(project_root).as_posix()

        if any(
            token in path.stem.lower()
            for token in (
                "worker",
                "queue",
                "job",
                "task",
                "scheduler",
                "cron",
            )
        ):
            files.add(relative)
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if _WORKER_PATTERN.search(source):
            files.add(relative)

    return tuple(sorted(files))


def worker_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a worker-topology finding."""
    files = discover_worker_files(project_root)

    if not files:
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "workers",
            "files": files,
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="workers",
            severity=BackendFindingSeverity.INFO,
            message="Backend workers or scheduled jobs detected.",
            evidence={
                "worker_file_count": str(len(files)),
                "worker_files": ",".join(files),
            },
        ),
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\backend\architecture.py" @'
"""Backend architecture classification for M4.2."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.backend.configuration import (
    discover_configuration_files,
)
from forge.domain_intelligence.backend.dependencies import (
    node_dependencies,
    python_dependencies,
)
from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)
from forge.domain_intelligence.backend.services import (
    discover_service_files,
)
from forge.domain_intelligence.backend.workers import (
    discover_worker_files,
)


def classify_backend_architecture(
    project_root: Path,
) -> str:
    """Classify backend layout using conservative local evidence."""
    service_files = discover_service_files(project_root)
    worker_files = discover_worker_files(project_root)
    configurations = discover_configuration_files(
        project_root
    )
    dependencies = {
        *node_dependencies(project_root),
        *python_dependencies(project_root),
    }

    has_docker = any(
        path.endswith(
            (
                "Dockerfile",
                "docker-compose.yml",
                "docker-compose.yaml",
            )
        )
        for path in configurations
    )
    has_queue = bool(
        dependencies.intersection(
            {
                "celery",
                "redis",
                "bull",
                "bullmq",
                "rq",
                "dramatiq",
            }
        )
    )

    if len(service_files) >= 4 and (worker_files or has_queue):
        return "modular-service-oriented"

    if has_docker and len(service_files) >= 2:
        return "containerized-service"

    if service_files:
        return "layered-backend"

    return "undetermined"


def architecture_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a conservative backend architecture finding."""
    classification = classify_backend_architecture(project_root)

    finding_id = backend_finding_identifier(
        {
            "category": "architecture",
            "classification": classification,
        }
    )

    severity = (
        BackendFindingSeverity.INFO
        if classification != "undetermined"
        else BackendFindingSeverity.LOW
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="architecture",
            severity=severity,
            message=(
                "Backend architecture classification: "
                f"{classification}"
            ),
            evidence={"classification": classification},
        ),
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_dependencies.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.backend.dependencies import (
    node_dependencies,
    python_dependencies,
)


def test_dependency_analysis_reads_node_and_python(
    tmp_path: Path,
) -> None:
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
    (tmp_path / "requirements.txt").write_text(
        "fastapi==0.116.0\nredis>=6\n",
        encoding="utf-8",
    )

    assert node_dependencies(tmp_path) == {
        "express": "^5.0.0"
    }
    assert set(python_dependencies(tmp_path)) == {
        "fastapi",
        "redis",
    }
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_configuration.py" @'
from pathlib import Path

from forge.domain_intelligence.backend.configuration import (
    discover_configuration_files,
)


def test_configuration_discovery_excludes_secrets(
    tmp_path: Path,
) -> None:
    (tmp_path / "pyproject.toml").write_text(
        "[project]\nname='api'\n",
        encoding="utf-8",
    )
    (tmp_path / ".env").write_text(
        "SECRET=value",
        encoding="utf-8",
    )

    assert discover_configuration_files(tmp_path) == (
        "pyproject.toml",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_services.py" @'
from pathlib import Path

from forge.domain_intelligence.backend.services import (
    discover_service_files,
)


def test_service_file_discovery(tmp_path: Path) -> None:
    services = tmp_path / "src" / "services"
    services.mkdir(parents=True)

    (services / "order_service.py").write_text(
        "class OrderService: pass",
        encoding="utf-8",
    )

    assert discover_service_files(tmp_path) == (
        "src/services/order_service.py",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_workers.py" @'
from pathlib import Path

from forge.domain_intelligence.backend.workers import (
    discover_worker_files,
)


def test_worker_file_discovery(tmp_path: Path) -> None:
    source = tmp_path / "src"
    source.mkdir()

    (source / "invoice_worker.ts").write_text(
        "export const run = () => undefined",
        encoding="utf-8",
    )

    assert discover_worker_files(tmp_path) == (
        "src/invoice_worker.ts",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_backend_architecture.py" @'
from pathlib import Path

from forge.domain_intelligence.backend.architecture import (
    classify_backend_architecture,
)


def test_architecture_classifies_layered_backend(
    tmp_path: Path,
) -> None:
    source = tmp_path / "services"
    source.mkdir()

    (source / "orders_service.py").write_text(
        "class OrdersService: pass",
        encoding="utf-8",
    )

    assert (
        classify_backend_architecture(tmp_path)
        == "layered-backend"
    )


def test_architecture_reports_undetermined(
    tmp_path: Path,
) -> None:
    assert (
        classify_backend_architecture(tmp_path)
        == "undetermined"
    )
'@

Write-Host ""
Write-Host "M4.2 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_backend_dependencies.py `
    .\tests\test_domain_intelligence_backend_configuration.py `
    .\tests\test_domain_intelligence_backend_services.py `
    .\tests\test_domain_intelligence_backend_workers.py `
    .\tests\test_domain_intelligence_backend_architecture.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.2 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.2 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short