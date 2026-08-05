"""React hook usage discovery for M4.1 Frontend Intelligence."""

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

_HOOK_PATTERN = re.compile(r"\b(use[A-Z][A-Za-z0-9_]*)\s*\(")


def extract_hook_names(source: str) -> tuple[str, ...]:
    """Extract built-in and custom React hook names."""
    return tuple(sorted(set(_HOOK_PATTERN.findall(source))))


def hook_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce findings for files that use React hooks."""
    findings: list[FrontendFinding] = []

    for path in sorted(
        project_root.rglob("*"),
        key=lambda item: item.as_posix(),
    ):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue

        if any(
            excluded in path.parts
            for excluded in ("node_modules", "dist", "build", ".next")
        ):
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        hooks = extract_hook_names(source)

        if not hooks:
            continue

        relative = path.relative_to(project_root).as_posix()
        finding_id = frontend_finding_identifier(
            {
                "category": "hooks",
                "path": relative,
                "hooks": hooks,
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="hooks",
                severity=FrontendFindingSeverity.INFO,
                message=f"React hook usage detected: {relative}",
                path=relative,
                evidence={
                    "hook_count": str(len(hooks)),
                    "hooks": ",".join(hooks),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )