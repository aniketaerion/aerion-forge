"""Deterministic report generation for Engineering Memory."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from forge.engineering_memory.errors import (
    EngineeringMemoryReportError,
)
from forge.engineering_memory.models import (
    EngineeringMemoryGeneration,
    EngineeringMemoryStatistics,
    MemoryRecord,
)


class EngineeringMemoryRenderer:
    """Build and atomically write Engineering Memory reports."""

    REPORT_NAMES = (
        "ENGINEERING_MEMORY.json",
        "ENGINEERING_MEMORY_SUMMARY.json",
        "ENGINEERING_MEMORY_LINEAGE.json",
        "ENGINEERING_MEMORY.md",
    )

    def render(
        self,
        records: tuple[MemoryRecord, ...],
        generation: EngineeringMemoryGeneration,
        statistics: EngineeringMemoryStatistics,
    ) -> dict[str, str]:
        """Build the complete deterministic report suite."""

        ordered_records = tuple(
            sorted(
                records,
                key=lambda record: record.memory_id,
            )
        )

        memory_payload = {
            "schema_version": "1.0",
            "generation": generation.model_dump(mode="json"),
            "statistics": statistics.model_dump(mode="json"),
            "records": [record.model_dump(mode="json") for record in ordered_records],
        }

        summary_payload = {
            "generation_id": generation.generation_id,
            "store_fingerprint": generation.store_fingerprint,
            "record_count": statistics.record_count,
            "relationship_count": statistics.relationship_count,
            "evidence_count": statistics.evidence_count,
            "mission_count": statistics.mission_count,
            "task_count": statistics.task_count,
            "assessment_count": statistics.assessment_count,
            "capability_count": statistics.capability_count,
            "permanent_record_count": (statistics.permanent_record_count),
            "memory_types": self._memory_type_counts(ordered_records),
        }

        lineage_payload = {
            "generation_id": generation.generation_id,
            "records": [
                {
                    "memory_id": record.memory_id,
                    "memory_type": record.memory_type.value,
                    "mission_ids": list(record.mission_ids),
                    "task_ids": list(record.task_ids),
                    "assessment_ids": list(record.assessment_ids),
                    "capability_ids": list(record.capability_ids),
                    "milestones": list(record.milestones),
                    "source_artifacts": list(record.source_artifacts),
                    "relationships": [
                        relationship.model_dump(mode="json")
                        for relationship in sorted(
                            record.relationships,
                            key=lambda item: item.relationship_id,
                        )
                    ],
                    "evidence": [
                        evidence.model_dump(mode="json")
                        for evidence in sorted(
                            record.evidence,
                            key=lambda item: item.evidence_id,
                        )
                    ],
                }
                for record in ordered_records
            ],
        }

        return {
            "ENGINEERING_MEMORY.json": self._json(memory_payload),
            "ENGINEERING_MEMORY_SUMMARY.json": self._json(summary_payload),
            "ENGINEERING_MEMORY_LINEAGE.json": self._json(lineage_payload),
            "ENGINEERING_MEMORY.md": self._markdown(
                ordered_records,
                generation,
                statistics,
            ),
        }

    def write(
        self,
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        """Atomically write a complete report suite."""

        supplied = set(reports)
        expected = set(self.REPORT_NAMES)

        if supplied != expected:
            missing = sorted(expected - supplied)
            extra = sorted(supplied - expected)

            raise EngineeringMemoryReportError(
                "Engineering Memory report set is incomplete "
                f"or invalid. Missing={missing}; extra={extra}."
            )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        snapshots = {
            report_name: (
                (directory / report_name).read_bytes()
                if (directory / report_name).exists()
                else None
            )
            for report_name in self.REPORT_NAMES
        }

        written: list[str] = []

        try:
            for report_name in self.REPORT_NAMES:
                path = directory / report_name
                content = reports[report_name].encode("utf-8")

                self._atomic_write(path, content)
                written.append(str(path))
        except Exception as exc:
            self._restore_reports(
                directory,
                snapshots,
            )

            if isinstance(
                exc,
                EngineeringMemoryReportError,
            ):
                raise

            raise EngineeringMemoryReportError(
                "Unable to write Engineering Memory reports."
            ) from exc

        return tuple(written)

    def _json(
        self,
        payload: Any,
    ) -> str:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
                default=str,
            )
            + "\n"
        )

    def _memory_type_counts(
        self,
        records: tuple[MemoryRecord, ...],
    ) -> dict[str, int]:
        counts: dict[str, int] = {}

        for record in records:
            key = record.memory_type.value
            counts[key] = counts.get(key, 0) + 1

        return {key: counts[key] for key in sorted(counts)}

    def _markdown(
        self,
        records: tuple[MemoryRecord, ...],
        generation: EngineeringMemoryGeneration,
        statistics: EngineeringMemoryStatistics,
    ) -> str:
        lines = [
            "# Engineering Memory",
            "",
            f"- Generation ID: `{generation.generation_id}`",
            (f"- Store fingerprint: `{generation.store_fingerprint}`"),
            f"- Records: {statistics.record_count}",
            (f"- Relationships: {statistics.relationship_count}"),
            f"- Evidence items: {statistics.evidence_count}",
            f"- Missions: {statistics.mission_count}",
            f"- Tasks: {statistics.task_count}",
            (f"- Impact assessments: {statistics.assessment_count}"),
            (f"- Capabilities: {statistics.capability_count}"),
            "",
            "## Memory Records",
            "",
        ]

        for record in records:
            lines.extend(
                [
                    f"### {record.title}",
                    "",
                    f"- Memory ID: `{record.memory_id}`",
                    f"- Type: `{record.memory_type.value}`",
                    (f"- Confidence: `{record.confidence.value}`"),
                    (f"- Retention: `{record.retention_policy.value}`"),
                    f"- Summary: {record.summary}",
                    f"- Rationale: {record.rationale}",
                    (
                        "- Missions: "
                        + (
                            ", ".join(f"`{item}`" for item in record.mission_ids)
                            if record.mission_ids
                            else "None"
                        )
                    ),
                    (
                        "- Tasks: "
                        + (
                            ", ".join(f"`{item}`" for item in record.task_ids)
                            if record.task_ids
                            else "None"
                        )
                    ),
                    (
                        "- Assessments: "
                        + (
                            ", ".join(f"`{item}`" for item in record.assessment_ids)
                            if record.assessment_ids
                            else "None"
                        )
                    ),
                    (
                        "- Capabilities: "
                        + (
                            ", ".join(f"`{item}`" for item in record.capability_ids)
                            if record.capability_ids
                            else "None"
                        )
                    ),
                    "",
                ]
            )

            if record.relationships:
                lines.extend(
                    [
                        "#### Relationships",
                        "",
                    ]
                )

                for relationship in record.relationships:
                    lines.append(
                        "- "
                        f"`{relationship.relationship_type.value}` "
                        f"→ `{relationship.target_memory_id}`"
                    )

                lines.append("")

            lines.extend(
                [
                    "#### Evidence",
                    "",
                ]
            )

            for evidence in record.evidence:
                lines.append(f"- `{evidence.evidence_type.value}`: {evidence.reference}")

            lines.append("")

        lines.extend(
            [
                "## Safety Boundary",
                "",
                (
                    "Engineering Memory stores verified, "
                    "deterministic engineering lineage only. "
                    "It does not execute tasks, modify source "
                    "code, run builds or tests, mutate Git, "
                    "deploy software, grant approvals, or "
                    "perform autonomous remediation."
                ),
                "",
            ]
        )

        return "\n".join(lines)

    def _restore_reports(
        self,
        directory: Path,
        snapshots: dict[str, bytes | None],
    ) -> None:
        for report_name, snapshot in snapshots.items():
            path = directory / report_name

            try:
                if snapshot is None:
                    path.unlink(missing_ok=True)
                else:
                    self._atomic_write(
                        path,
                        snapshot,
                    )
            except Exception as exc:
                raise EngineeringMemoryReportError(
                    "Engineering Memory report rollback failed."
                ) from exc

    def _atomic_write(
        self,
        path: Path,
        content: bytes,
    ) -> None:
        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary: Path | None = None

        try:
            descriptor, name = tempfile.mkstemp(
                prefix=f".{path.name}.",
                suffix=".tmp",
                dir=path.parent,
            )
            temporary = Path(name)

            with os.fdopen(descriptor, "wb") as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(
                temporary,
                path,
            )
            temporary = None
        except OSError as exc:
            raise EngineeringMemoryReportError(
                f"Atomic Engineering Memory report replacement failed: {path.name}"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
