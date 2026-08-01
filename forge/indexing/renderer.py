"""Deterministic project-index report rendering."""

import json

from forge.indexing.models import IndexChange, IndexResult


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n"


def _paths(changes: list[IndexChange]) -> str:
    if not changes:
        return "None."
    lines: list[str] = []
    for change in changes:
        moved = f" (from `{change.previous_path}`)" if change.previous_path else ""
        lines.append(f"- `{change.path}`{moved}")
    return "\n".join(lines)


class IndexRenderer:
    """Render the portable JSON catalog and Markdown index summaries."""

    def render(self, result: IndexResult) -> dict[str, str]:
        """Return all required deterministic report contents."""
        project = result.project_index.model_dump(mode="json")
        generation = project["generation"]
        changes = result.changes.model_dump(mode="json")
        portable_project = {
            "schema_version": project["schema_version"],
            "generation": generation,
        }
        return {
            "PROJECT_INDEX.json": _json(portable_project),
            "INDEX_SUMMARY.json": _json(generation),
            "INDEX_CHANGES.json": _json(changes),
            "FILE_CATALOG.json": _json({"files": project["files"]}),
            "INDEX_SUMMARY.md": self._summary(result),
            "INDEX_CHANGES.md": self._changes(result),
        }

    @staticmethod
    def _summary(result: IndexResult) -> str:
        generation = result.project_index.generation
        statistics = generation.statistics
        return f"""# Project Index Summary

- Repository: `{generation.repository_name}`
- Schema: `{generation.schema_version}`
- Generation: `{generation.generation_id}`
- Previous generation: `{generation.previous_generation_id or "none"}`
- Repository state: `{generation.repository_state_fingerprint}`
- Indexed files: {statistics.total_indexed_files}
- Added: {statistics.added_count}
- Modified: {statistics.modified_count}
- Removed: {statistics.removed_count}
- Renamed: {statistics.renamed_count}
- Unchanged: {statistics.unchanged_count}
- Failed: {statistics.failed_count}
- Skipped: {statistics.skipped_count}
"""

    @staticmethod
    def _changes(result: IndexResult) -> str:
        changes = result.changes
        return f"""# Project Index Changes

## Added

{_paths(changes.added)}

## Modified

{_paths(changes.modified)}

## Removed

{_paths(changes.removed)}

## Renamed or Moved

{_paths(changes.renamed)}

## Failed

{_paths(changes.failed)}

## Skipped

{_paths(changes.skipped)}
"""
