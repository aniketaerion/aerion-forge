"""Static embedded safety analysis for M4.6 Package 2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.embedded.identifiers import (
    embedded_finding_identifier,
)
from forge.domain_intelligence.embedded.models import (
    EmbeddedFinding,
    EmbeddedFindingSeverity,
)

_SAFETY_PATTERNS: tuple[
    tuple[str, EmbeddedFindingSeverity, re.Pattern[str], str],
    ...,
] = (
    (
        "unsafe-memory",
        EmbeddedFindingSeverity.HIGH,
        re.compile(r"\b(?:strcpy|strcat|gets)\s*\("),
        "Potentially unsafe C string operation detected.",
    ),
    (
        "blocking-delay",
        EmbeddedFindingSeverity.MEDIUM,
        re.compile(r"\b(?:sleep|usleep|HAL_Delay)\s*\("),
        "Blocking delay detected in embedded code.",
    ),
    (
        "watchdog",
        EmbeddedFindingSeverity.MEDIUM,
        re.compile(r"\bwatchdog\b", re.IGNORECASE),
        "Watchdog-related logic requires review.",
    ),
    (
        "failsafe",
        EmbeddedFindingSeverity.INFO,
        re.compile(r"\bfailsafe\b", re.IGNORECASE),
        "Failsafe-related logic detected.",
    ),
)

_CODE_SUFFIXES = {
    ".c",
    ".cc",
    ".cpp",
    ".cxx",
    ".h",
    ".hh",
    ".hpp",
    ".hxx",
    ".py",
}


def analyze_embedded_safety(
    project_root: Path,
) -> tuple[EmbeddedFinding, ...]:
    """Produce deterministic safety findings from source text."""
    findings: list[EmbeddedFinding] = []

    for path in sorted(project_root.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in _CODE_SUFFIXES:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "build",
                "install",
                "dist",
                "__pycache__",
            )
        ):
            continue

        try:
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        relative = path.relative_to(project_root).as_posix()

        for category, severity, pattern, message in _SAFETY_PATTERNS:
            if not pattern.search(content):
                continue

            payload = {
                "category": category,
                "path": relative,
                "message": message,
            }
            findings.append(
                EmbeddedFinding(
                    finding_id=embedded_finding_identifier(payload),
                    category=category,
                    severity=severity,
                    message=message,
                    path=relative,
                )
            )

    return tuple(
        sorted(
            findings,
            key=lambda item: (
                item.severity.value,
                item.category,
                item.path or "",
                item.finding_id,
            ),
        )
    )