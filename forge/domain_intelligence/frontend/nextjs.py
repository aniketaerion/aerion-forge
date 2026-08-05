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