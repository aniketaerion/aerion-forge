"""Incremental comparison, generation, persistence, and reporting orchestration."""

import hashlib
import logging
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from forge.indexing.errors import IndexReportError
from forge.indexing.models import (
    INDEX_SCHEMA_VERSION,
    ChangeType,
    IndexChange,
    IndexChangeSet,
    IndexConfiguration,
    IndexedFile,
    IndexGeneration,
    IndexResult,
    IndexStatistics,
    IndexStatus,
    ProjectIndex,
)
from forge.indexing.renderer import IndexRenderer
from forge.indexing.scanner import ProjectIndexScanner
from forge.indexing.store import ProjectIndexStore


class IndexingService:
    """Build a complete current state and commit it only after successful reporting."""

    def __init__(
        self,
        store: ProjectIndexStore,
        reports_path: Path,
        logger: logging.Logger,
        configuration: IndexConfiguration,
        renderer: IndexRenderer | None = None,
    ) -> None:
        self.store = store
        self.reports_path = reports_path.resolve()
        self.logger = logger
        self.configuration = configuration
        self.renderer = renderer or IndexRenderer()

    def index(self, root: Path, workspace_id: str | None = None) -> IndexResult:
        """Scan, compare, report, and atomically persist one repository index."""
        scanner = ProjectIndexScanner(
            root,
            self.configuration.max_hash_bytes,
            self.configuration.hash_chunk_bytes,
            self.configuration.max_files,
            excluded_files={self.store.path},
        )
        resolved_root, files = scanner.scan()
        identity = workspace_id or self.repository_identity(resolved_root)
        previous = self.store.get(identity)
        changes = self._compare(previous.files if previous else [], files)
        state = self._state_fingerprint(files)
        generation_id = f"gen-{state[:20]}"
        previous_generation_id = None
        if previous:
            previous_generation_id = (
                previous.generation.previous_generation_id
                if previous.generation.repository_state_fingerprint == state
                else previous.generation.generation_id
            )
        observed = [
            item.model_copy(update={"last_observed_generation": generation_id}) for item in files
        ]
        statistics = self._statistics(observed, changes)
        generation = IndexGeneration(
            repository_identity=identity,
            repository_name=resolved_root.name,
            workspace_id=workspace_id,
            generation_id=generation_id,
            previous_generation_id=previous_generation_id,
            repository_state_fingerprint=state,
            statistics=statistics,
        )
        project_index = ProjectIndex(generation=generation, files=observed)
        result = IndexResult(project_index=project_index, changes=changes)
        self._write_reports(result)
        self.store.save(identity, project_index)
        self.logger.info(
            "Project index completed",
            extra={
                "context": {
                    "repository": resolved_root.name,
                    "state": state,
                    "files": statistics.total_indexed_files,
                }
            },
        )
        return result

    @staticmethod
    def repository_identity(root: Path) -> str:
        """Return a stable direct-path persistence identity without exposing the path."""
        normalized = str(root.resolve()).replace("\\", "/").casefold()
        return hashlib.sha256(normalized.encode()).hexdigest()

    @staticmethod
    def _state_fingerprint(files: list[IndexedFile]) -> str:
        digest = hashlib.sha256()
        digest.update(f"schema:{INDEX_SCHEMA_VERSION}\n".encode())
        for item in sorted(files, key=lambda value: value.normalized_path):
            stable = "|".join(
                (
                    item.normalized_path,
                    item.fingerprint.value or "",
                    item.fingerprint.strategy.value,
                    item.category.value,
                    item.engineering_role.value,
                    item.repository_area or "",
                    item.index_status.value,
                )
            )
            digest.update(f"{stable}\n".encode())
        return digest.hexdigest()

    def _compare(
        self, previous_files: list[IndexedFile], current_files: list[IndexedFile]
    ) -> IndexChangeSet:
        previous = {item.normalized_path: item for item in previous_files}
        current = {item.normalized_path: item for item in current_files}
        added_paths = set(current) - set(previous)
        removed_paths = set(previous) - set(current)
        renamed: list[IndexChange] = []
        previous_by_fingerprint: dict[str, list[str]] = defaultdict(list)
        current_by_fingerprint: dict[str, list[str]] = defaultdict(list)
        for path in removed_paths:
            value = previous[path].fingerprint.value
            if value:
                previous_by_fingerprint[value].append(path)
        for path in added_paths:
            value = current[path].fingerprint.value
            if value:
                current_by_fingerprint[value].append(path)
        for fingerprint in sorted(set(previous_by_fingerprint) & set(current_by_fingerprint)):
            old_matches = previous_by_fingerprint[fingerprint]
            new_matches = current_by_fingerprint[fingerprint]
            if len(old_matches) == 1 and len(new_matches) == 1:
                old_path, new_path = old_matches[0], new_matches[0]
                renamed.append(
                    IndexChange(
                        change_type=ChangeType.RENAMED,
                        path=current[new_path].path,
                        previous_path=previous[old_path].path,
                        fingerprint=fingerprint,
                    )
                )
                removed_paths.remove(old_path)
                added_paths.remove(new_path)

        changes = IndexChangeSet(renamed=renamed)
        for path in sorted(added_paths):
            item = current[path]
            if item.index_status is IndexStatus.FAILED:
                changes.failed.append(self._change(item, ChangeType.FAILED))
            elif item.index_status is IndexStatus.SKIPPED:
                changes.skipped.append(self._change(item, ChangeType.SKIPPED))
            else:
                changes.added.append(self._change(item, ChangeType.ADDED))
        for path in sorted(removed_paths):
            changes.removed.append(self._change(previous[path], ChangeType.REMOVED))
        for path in sorted(set(previous) & set(current)):
            old, new = previous[path], current[path]
            if new.index_status is IndexStatus.FAILED:
                changes.failed.append(self._change(new, ChangeType.FAILED))
            elif new.index_status is IndexStatus.SKIPPED:
                changes.skipped.append(self._change(new, ChangeType.SKIPPED))
            elif self._comparison_signature(old) != self._comparison_signature(new):
                changes.modified.append(self._change(new, ChangeType.MODIFIED))
            else:
                changes.unchanged.append(self._change(new, ChangeType.UNCHANGED))
        return changes

    @staticmethod
    def _comparison_signature(item: IndexedFile) -> tuple[Any, ...]:
        return (
            item.fingerprint.value,
            item.fingerprint.strategy,
            item.category,
            item.engineering_role,
            item.repository_area,
            item.index_status,
            item.binary,
            item.generated,
        )

    @staticmethod
    def _change(item: IndexedFile, change_type: ChangeType) -> IndexChange:
        return IndexChange(
            change_type=change_type,
            path=item.path,
            fingerprint=item.fingerprint.value,
        )

    @staticmethod
    def _statistics(files: list[IndexedFile], changes: IndexChangeSet) -> IndexStatistics:
        indexed = [item for item in files if item.index_status is IndexStatus.INDEXED]
        return IndexStatistics(
            total_indexed_files=len(indexed),
            by_category=dict(sorted(Counter(item.category.value for item in indexed).items())),
            by_extension=dict(
                sorted(Counter(item.extension or "[none]" for item in indexed).items())
            ),
            by_engineering_role=dict(
                sorted(Counter(item.engineering_role.value for item in indexed).items())
            ),
            added_count=len(changes.added),
            modified_count=len(changes.modified),
            removed_count=len(changes.removed),
            renamed_count=len(changes.renamed),
            unchanged_count=len(changes.unchanged),
            failed_count=len(changes.failed),
            skipped_count=len(changes.skipped),
        )

    def _write_reports(self, result: IndexResult) -> None:
        self.reports_path.mkdir(parents=True, exist_ok=True)
        temporary_files: list[tuple[Path, Path]] = []
        try:
            for filename, content in self.renderer.render(result).items():
                destination = (self.reports_path / filename).resolve()
                if self.reports_path not in destination.parents:
                    raise IndexReportError("Index report path escapes configured directory")
                temporary = destination.with_suffix(f"{destination.suffix}.tmp")
                temporary.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
                temporary_files.append((temporary, destination))
            for temporary, destination in temporary_files:
                temporary.replace(destination)
        except (OSError, ValueError) as exc:
            for temporary, _ in temporary_files:
                temporary.unlink(missing_ok=True)
            raise IndexReportError(f"Unable to write index reports: {exc}") from exc
