"""Routing discovery for M4.1 Frontend Intelligence."""

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

_ROUTE_PATTERN = re.compile(
    r"<Route\b[^>]*\bpath\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

_NEXT_ROUTE_FILES = {
    "page.js",
    "page.jsx",
    "page.ts",
    "page.tsx",
    "route.js",
    "route.ts",
}


def discover_route_files(project_root: Path) -> tuple[Path, ...]:
    """Return route configuration and convention-based route files."""
    candidates: set[Path] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            excluded in path.parts
            for excluded in ("node_modules", "dist", "build", ".next")
        ):
            continue

        if path.name in _NEXT_ROUTE_FILES:
            candidates.add(path)
            continue

        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if "<Route" in source or "createBrowserRouter" in source:
            candidates.add(path)

    return tuple(sorted(candidates, key=lambda path: path.as_posix()))


def extract_route_paths(source: str) -> tuple[str, ...]:
    """Extract explicit React Router paths."""
    return tuple(sorted(set(_ROUTE_PATTERN.findall(source))))


def route_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce findings for explicit and convention-based routes."""
    findings: list[FrontendFinding] = []

    for path in discover_route_files(project_root):
        relative = path.relative_to(project_root).as_posix()

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            source = ""

        routes = extract_route_paths(source)

        if not routes and path.name in _NEXT_ROUTE_FILES:
            routes = (relative,)

        finding_id = frontend_finding_identifier(
            {
                "category": "routing",
                "path": relative,
                "routes": routes,
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="routing",
                severity=FrontendFindingSeverity.INFO,
                message=f"Frontend routing detected: {relative}",
                path=relative,
                evidence={
                    "route_count": str(len(routes)),
                    "routes": ",".join(routes),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )