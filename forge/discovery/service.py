"""Repository discovery orchestration and persistence."""

import hashlib
import logging
from pathlib import Path
from typing import Any

from forge.discovery.models import DiscoveryResult
from forge.discovery.renderer import DiscoveryRenderer
from forge.discovery.scanner import RepositoryDiscoveryScanner
from forge.memory import JsonMemoryStore


class DiscoveryService:
    """Run discovery, persist results, and atomically write report artifacts."""

    def __init__(
        self,
        store: JsonMemoryStore,
        reports_path: Path,
        logger: logging.Logger,
        renderer: DiscoveryRenderer | None = None,
    ) -> None:
        self.store = store
        self.reports_path = reports_path.resolve()
        self.logger = logger
        self.renderer = renderer or DiscoveryRenderer()

    def inspect(self, root: Path, workspace_id: str | None = None) -> DiscoveryResult:
        """Discover one repository and persist its latest deterministic result."""
        self.logger.info("Repository discovery started", extra={"context": {"root": str(root)}})
        result = RepositoryDiscoveryScanner(root).scan()
        self._write_reports(result)
        key = (
            workspace_id
            or hashlib.sha256(str(result.repository_root).casefold().encode("utf-8")).hexdigest()
        )
        records = self.store.read("results")
        if records is None:
            records = {}
        if not isinstance(records, dict):
            raise RuntimeError("Discovery memory results must be a JSON object")
        updated: dict[str, Any] = dict(records)
        updated[key] = result.model_dump(mode="json")
        self.store.set("results", updated)
        self.store.set("latest_result_id", key)
        self.logger.info(
            "Repository discovery completed",
            extra={"context": {"root": str(result.repository_root), "files": result.file_count}},
        )
        return result

    def _write_reports(self, result: DiscoveryResult) -> None:
        self.reports_path.mkdir(parents=True, exist_ok=True)
        for filename, content in self.renderer.render(result).items():
            destination = (self.reports_path / filename).resolve()
            if self.reports_path not in destination.parents:
                raise ValueError("Discovery report path escapes the configured directory")
            temporary = destination.with_suffix(f"{destination.suffix}.tmp")
            temporary.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
            temporary.replace(destination)
