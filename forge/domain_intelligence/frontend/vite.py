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