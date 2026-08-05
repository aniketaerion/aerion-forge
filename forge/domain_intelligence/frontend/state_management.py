"""Frontend state-management discovery for M4.1."""

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

_STATE_PACKAGES: dict[str, str] = {
    "@reduxjs/toolkit": "redux-toolkit",
    "redux": "redux",
    "zustand": "zustand",
    "mobx": "mobx",
    "jotai": "jotai",
    "recoil": "recoil",
    "xstate": "xstate",
}


def detect_state_management(project_root: Path) -> tuple[str, ...]:
    """Detect common state-management libraries."""
    dependencies = package_dependencies(
        load_package_json(project_root)
    )

    detected = {
        label
        for package_name, label in _STATE_PACKAGES.items()
        if package_name in dependencies
    }

    return tuple(sorted(detected))


def state_management_findings(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    """Produce deterministic findings for detected state libraries."""
    findings: list[FrontendFinding] = []

    for library in detect_state_management(project_root):
        finding_id = frontend_finding_identifier(
            {
                "category": "state_management",
                "library": library,
                "root": project_root.as_posix(),
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="state_management",
                severity=FrontendFindingSeverity.INFO,
                message=f"State-management library detected: {library}",
                path="package.json",
                evidence={"library": library},
            )
        )

    return tuple(findings)