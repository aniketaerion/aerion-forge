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