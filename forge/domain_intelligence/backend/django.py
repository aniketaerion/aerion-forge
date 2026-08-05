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