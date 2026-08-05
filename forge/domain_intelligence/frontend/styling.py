"""Frontend styling discovery for M4.1."""

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
)

_STYLE_PACKAGES: dict[str, str] = {
    "tailwindcss": "tailwindcss",
    "styled-components": "styled-components",
    "@emotion/react": "emotion",
    "sass": "sass",
    "less": "less",
    "@mui/material": "mui",
    "bootstrap": "bootstrap",
}


def detect_styling_technologies(
    project_root: Path,
) -> tuple[str, ...]:
    """Detect styling libraries and source conventions."""
    dependencies = package_dependencies(
        load_package_json(project_root)
    )

    detected = {
        label
        for package_name, label in _STYLE_PACKAGES.items()
        if package_name in dependencies
    }

    if any(project_root.rglob("*.module.css")):
        detected.add("css-modules")

    if any(project_root.rglob("*.scss")):
        detected.add("scss")

    if any(project_root.rglob("*.css")):
        detected.add("css")

    return tuple(sorted(detected))


def styling_findings(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    """Produce deterministic findings for styling technologies."""
    findings: list[FrontendFinding] = []

    for technology in detect_styling_technologies(project_root):
        finding_id = frontend_finding_identifier(
            {
                "category": "styling",
                "technology": technology,
                "root": project_root.as_posix(),
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="styling",
                severity=FrontendFindingSeverity.INFO,
                message=f"Styling technology detected: {technology}",
                evidence={"technology": technology},
            )
        )

    return tuple(findings)