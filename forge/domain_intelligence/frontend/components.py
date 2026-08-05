"""Component discovery for M4.1 Frontend Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
)

_COMPONENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfunction\s+([A-Z][A-Za-z0-9_]*)\s*\("),
    re.compile(r"\bclass\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+React\.Component"),
    re.compile(r"\bconst\s+([A-Z][A-Za-z0-9_]*)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>"),
)

_COMPONENT_SUFFIXES = {".jsx", ".tsx"}


def discover_component_files(project_root: Path) -> tuple[Path, ...]:
    """Return deterministic React component source files."""
    files = [
        path
        for path in project_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in _COMPONENT_SUFFIXES
        and "node_modules" not in path.parts
        and "dist" not in path.parts
        and "build" not in path.parts
        and ".next" not in path.parts
    ]

    return tuple(sorted(files, key=lambda path: path.as_posix()))


def extract_component_names(source: str) -> tuple[str, ...]:
    """Extract likely component names without executing source code."""
    names: set[str] = set()

    for pattern in _COMPONENT_PATTERNS:
        names.update(pattern.findall(source))

    return tuple(sorted(names))


def component_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce one finding per discovered component file."""
    findings: list[FrontendFinding] = []

    for path in discover_component_files(project_root):
        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        names = extract_component_names(source)

        if not names:
            continue

        relative = path.relative_to(project_root).as_posix()
        finding_id = frontend_finding_identifier(
            {
                "category": "component",
                "path": relative,
                "names": names,
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="component",
                severity=FrontendFindingSeverity.INFO,
                message=f"React component file detected: {relative}",
                path=relative,
                evidence={
                    "component_count": str(len(names)),
                    "components": ",".join(names),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )