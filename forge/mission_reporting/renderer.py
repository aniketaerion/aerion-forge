"""Deterministic Mission Reporting renderer."""

import json
import os
import tempfile
from collections.abc import Mapping
from pathlib import Path

from forge.mission_reporting.errors import (
    MissionReportingReportError,
)
from forge.mission_reporting.models import (
    MissionReport,
    MissionReportRisk,
    MissionTraceabilityItem,
)

REPORT_NAMES = (
    "MISSION_REPORT.json",
    "MISSION_SUMMARY.json",
    "MISSION_TRACEABILITY.json",
    "MISSION_RISKS.json",
    "MISSION_REPORT.md",
)


class MissionReportRenderer:
    """Render and persist deterministic Mission Report outputs."""

    def render(
        self,
        report: MissionReport,
    ) -> Mapping[str, bytes]:
        """Render the complete Mission Report output suite."""

        payloads = {
            "MISSION_REPORT.json": self._json_bytes(report.model_dump(mode="json")),
            "MISSION_SUMMARY.json": self._json_bytes(self._summary_payload(report)),
            "MISSION_TRACEABILITY.json": self._json_bytes(self._traceability_payload(report)),
            "MISSION_RISKS.json": self._json_bytes(self._risks_payload(report)),
            "MISSION_REPORT.md": self._markdown(report).encode("utf-8"),
        }

        return {name: payloads[name] for name in REPORT_NAMES}

    def write(
        self,
        directory: Path,
        rendered: Mapping[str, bytes],
    ) -> tuple[Path, ...]:
        """Write the complete report suite atomically."""

        expected = set(REPORT_NAMES)
        actual = set(rendered)

        missing = expected - actual
        extra = actual - expected

        if missing:
            raise MissionReportingReportError(
                "Mission Reporting output is missing: " + ", ".join(sorted(missing))
            )

        if extra:
            raise MissionReportingReportError(
                "Mission Reporting output contains unexpected files: " + ", ".join(sorted(extra))
            )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        snapshots = {
            name: ((directory / name).read_bytes() if (directory / name).exists() else None)
            for name in REPORT_NAMES
        }

        written: list[Path] = []

        try:
            for name in REPORT_NAMES:
                path = directory / name

                self._atomic_write(
                    path,
                    rendered[name],
                )
                written.append(path)
        except Exception:
            self._restore_reports(
                directory,
                snapshots,
            )
            raise

        return tuple(written)

    def _summary_payload(
        self,
        report: MissionReport,
    ) -> dict[str, object]:
        return {
            "schema_version": report.schema_version,
            "report_id": report.report_id,
            "report_fingerprint": report.report_fingerprint,
            "mission_id": report.mission_id,
            "title": report.title,
            "status": report.status.value,
            "executive_summary": report.executive_summary,
            "statistics": report.statistics.model_dump(mode="json"),
            "section_types": [section.section_type.value for section in report.sections],
            "source_fingerprints": dict(report.source_fingerprints),
        }

    def _traceability_payload(
        self,
        report: MissionReport,
    ) -> dict[str, object]:
        return {
            "schema_version": report.schema_version,
            "report_id": report.report_id,
            "mission_id": report.mission_id,
            "traceability_count": len(report.traceability),
            "traceability": [self._traceability_item_payload(item) for item in report.traceability],
        }

    def _risks_payload(
        self,
        report: MissionReport,
    ) -> dict[str, object]:
        return {
            "schema_version": report.schema_version,
            "report_id": report.report_id,
            "mission_id": report.mission_id,
            "risk_count": len(report.risks),
            "risks": [self._risk_payload(risk) for risk in report.risks],
        }

    def _traceability_item_payload(
        self,
        item: MissionTraceabilityItem,
    ) -> dict[str, object]:
        return item.model_dump(mode="json")

    def _risk_payload(
        self,
        risk: MissionReportRisk,
    ) -> dict[str, object]:
        return risk.model_dump(mode="json")

    def _markdown(
        self,
        report: MissionReport,
    ) -> str:
        lines = [
            f"# {report.title}",
            "",
            f"Report ID: `{report.report_id}`  ",
            f"Mission ID: `{report.mission_id}`  ",
            f"Status: **{report.status.value}**  ",
            (f"Report fingerprint: `{report.report_fingerprint}`"),
            "",
            "## Executive Summary",
            "",
            report.executive_summary,
            "",
            "## Statistics",
            "",
            f"- Tasks: {report.statistics.task_count}",
            (f"- Blocked tasks: {report.statistics.blocked_task_count}"),
            f"- Risks: {report.statistics.risk_count}",
            (f"- Traceability relationships: {report.statistics.traceability_count}"),
            (f"- Engineering Memory records: {report.statistics.engineering_memory_record_count}"),
            "",
        ]

        for section in report.sections:
            lines.extend(
                [
                    f"## {section.title}",
                    "",
                    section.summary,
                    "",
                ]
            )

            for item in section.content:
                lines.append(f"- {item}")

            if section.content:
                lines.append("")

        lines.extend(
            [
                "## Safety Boundary",
                "",
                (
                    "Mission Reporting summarizes verified and "
                    "deterministic engineering artifacts only."
                ),
                (
                    "It does not execute tasks, modify source code, "
                    "run builds or tests, mutate Git, deploy software, "
                    "grant approvals, or perform autonomous remediation."
                ),
                "",
            ]
        )

        return "\n".join(lines)

    def _json_bytes(
        self,
        payload: object,
    ) -> bytes:
        return (
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                separators=(",", ": "),
            )
            + "\n"
        ).encode("utf-8")

    def _restore_reports(
        self,
        directory: Path,
        snapshots: Mapping[str, bytes | None],
    ) -> None:
        for name, snapshot in snapshots.items():
            path = directory / name

            try:
                if snapshot is None:
                    path.unlink(missing_ok=True)
                else:
                    self._atomic_write(
                        path,
                        snapshot,
                    )
            except Exception as exc:
                raise MissionReportingReportError("Mission Reporting rollback failed.") from exc

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

            with os.fdopen(
                descriptor,
                "wb",
            ) as stream:
                stream.write(content)
                stream.flush()
                os.fsync(stream.fileno())

            os.replace(
                temporary,
                path,
            )
            temporary = None
        except OSError as exc:
            raise MissionReportingReportError(
                f"Atomic Mission Reporting file replacement failed: {path.name}"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
