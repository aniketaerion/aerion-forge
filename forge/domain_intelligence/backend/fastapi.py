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