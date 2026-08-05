"""Backend worker and scheduled-job discovery for M4.2."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.backend.identifiers import (
    backend_finding_identifier,
)
from forge.domain_intelligence.backend.models import (
    BackendFinding,
    BackendFindingSeverity,
)

_WORKER_PATTERN = re.compile(
    r"\b(celery|bullmq|bull|rq|dramatiq|apscheduler|cron|worker_threads)\b",
    re.IGNORECASE,
)


def discover_worker_files(
    project_root: Path,
) -> tuple[str, ...]:
    """Discover likely worker, queue, and scheduled-job files."""
    files: set[str] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {
            ".js",
            ".mjs",
            ".cjs",
            ".ts",
            ".py",
        }:
            continue

        if any(
            excluded in path.parts
            for excluded in (
                ".git",
                ".venv",
                "venv",
                "node_modules",
                "__pycache__",
                "dist",
                "build",
            )
        ):
            continue

        relative = path.relative_to(project_root).as_posix()

        if any(
            token in path.stem.lower()
            for token in (
                "worker",
                "queue",
                "job",
                "task",
                "scheduler",
                "cron",
            )
        ):
            files.add(relative)
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if _WORKER_PATTERN.search(source):
            files.add(relative)

    return tuple(sorted(files))


def worker_findings(
    project_root: Path,
) -> tuple[BackendFinding, ...]:
    """Produce a worker-topology finding."""
    files = discover_worker_files(project_root)

    if not files:
        return ()

    finding_id = backend_finding_identifier(
        {
            "category": "workers",
            "files": files,
        }
    )

    return (
        BackendFinding(
            finding_id=finding_id,
            category="workers",
            severity=BackendFindingSeverity.INFO,
            message="Backend workers or scheduled jobs detected.",
            evidence={
                "worker_file_count": str(len(files)),
                "worker_files": ",".join(files),
            },
        ),
    )