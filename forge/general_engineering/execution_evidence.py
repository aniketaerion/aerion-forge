"""Execution evidence helpers for M5.9 Package 5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.safe_code_editing.models import SafeEditReport


@dataclass(frozen=True)
class FileExecutionEvidence:
    path: str
    changed: bool
    original_fingerprint: str
    resulting_fingerprint: str


def summarize_execution_report(
    report: SafeEditReport,
) -> tuple[FileExecutionEvidence, ...]:
    return tuple(
        FileExecutionEvidence(
            path=result.relative_path,
            changed=result.changed,
            original_fingerprint=result.original_fingerprint,
            resulting_fingerprint=result.resulting_fingerprint,
        )
        for result in report.file_results
    )