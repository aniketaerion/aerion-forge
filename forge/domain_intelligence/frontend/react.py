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