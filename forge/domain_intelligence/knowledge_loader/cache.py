"""Deterministic cache support for M4.7 Package 2."""

from __future__ import annotations

import json
from pathlib import Path

from forge.domain_intelligence.knowledge_loader.models import (
    KnowledgeLoadReport,
)


class KnowledgeCache:
    """Read and write derived knowledge-loader cache files."""

    def __init__(self, cache_root: Path) -> None:
        self._cache_root = cache_root

    def report_path(self, report_id: str) -> Path:
        return self._cache_root / f"{report_id}.json"

    def write(self, report: KnowledgeLoadReport) -> Path:
        self._cache_root.mkdir(parents=True, exist_ok=True)
        path = self.report_path(report.report_id)
        path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        return path

    def read(self, report_id: str) -> KnowledgeLoadReport | None:
        path = self.report_path(report_id)
        if not path.is_file():
            return None

        payload = json.loads(path.read_text(encoding="utf-8"))
        return KnowledgeLoadReport.model_validate(payload)