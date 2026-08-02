"""Deterministic report generation for Impact Decision."""

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from forge.impact.errors import ImpactReportError
from forge.impact.models import (
    ImpactAssessment,
    ImpactDecisionGeneration,
)


class ImpactRenderer:
    """Build and atomically write Impact Decision reports."""

    REPORT_NAMES = (
        "IMPACT_ASSESSMENT.json",
        "IMPACT_DECISION.json",
        "IMPACT_EVIDENCE.json",
        "IMPACT_SUMMARY.md",
    )

    def render(
        self,
        assessment: ImpactAssessment,
        generation: ImpactDecisionGeneration,
    ) -> dict[str, str]:
        """Build the complete deterministic report suite."""

        assessment_payload = assessment.model_dump(mode="json")
        generation_payload = generation.model_dump(mode="json")

        decision_payload = {
            "assessment_id": assessment.assessment_id,
            "mission_id": assessment.mission_id,
            "status": assessment.status.value,
            "overall_severity": assessment.overall_severity.value,
            "confidence": assessment.confidence.value,
            "blocking_reason": assessment.blocking_reason,
            "recommendation": assessment.recommendation.model_dump(mode="json"),
            "generation": generation_payload,
        }

        evidence_payload = {
            "assessment_id": assessment.assessment_id,
            "task_ids": list(assessment.task_ids),
            "source_fingerprints": dict(sorted(assessment.source_fingerprints.items())),
            "findings": [finding.model_dump(mode="json") for finding in assessment.findings],
        }

        return {
            "IMPACT_ASSESSMENT.json": self._json(assessment_payload),
            "IMPACT_DECISION.json": self._json(decision_payload),
            "IMPACT_EVIDENCE.json": self._json(evidence_payload),
            "IMPACT_SUMMARY.md": self._markdown(
                assessment,
                generation,
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

            raise ImpactReportError(
                f"Impact report set is incomplete or invalid. Missing={missing}; extra={extra}."
            )

        directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        written: list[str] = []

        for report_name in self.REPORT_NAMES:
            path = directory / report_name
            content = reports[report_name].encode("utf-8")

            try:
                self._atomic_write(path, content)
            except ImpactReportError:
                raise
            except Exception as exc:
                raise ImpactReportError(f"Unable to write impact report: {report_name}") from exc

            written.append(str(path))

        return tuple(written)

    def _json(self, payload: Any) -> str:
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

    def _markdown(
        self,
        assessment: ImpactAssessment,
        generation: ImpactDecisionGeneration,
    ) -> str:
        lines = [
            "# Impact Decision Summary",
            "",
            f"- Assessment ID: `{assessment.assessment_id}`",
            f"- Mission ID: `{assessment.mission_id}`",
            f"- Generation ID: `{generation.generation_id}`",
            f"- Status: `{assessment.status.value}`",
            (f"- Overall severity: `{assessment.overall_severity.value}`"),
            f"- Confidence: `{assessment.confidence.value}`",
            f"- Findings: {len(assessment.findings)}",
            f"- Affected tasks: {len(assessment.task_ids)}",
            "",
            "## Recommendation",
            "",
            (f"- Selected option: `{assessment.recommendation.selected_option_id}`"),
            f"- Rationale: {assessment.recommendation.rationale}",
        ]

        if assessment.blocking_reason is not None:
            lines.extend(
                [
                    "",
                    "## Blocking Condition",
                    "",
                    assessment.blocking_reason,
                ]
            )

        lines.extend(
            [
                "",
                "## Findings",
                "",
            ]
        )

        for finding in assessment.findings:
            lines.extend(
                [
                    f"### {finding.finding_id}",
                    "",
                    f"- Severity: `{finding.severity.value}`",
                    f"- Category: `{finding.category.value}`",
                    f"- Scope: `{finding.scope.value}`",
                    f"- Summary: {finding.summary}",
                    f"- Rationale: {finding.rationale}",
                    "",
                ]
            )

        lines.extend(
            [
                "## Safety Boundary",
                "",
                (
                    "This report provides deterministic impact analysis "
                    "only. It does not execute tasks, modify source code, "
                    "run builds or tests, perform migrations, mutate Git, "
                    "deploy software, grant approvals, or remediate issues."
                ),
                "",
            ]
        )

        return "\n".join(lines)

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

            os.replace(temporary, path)
            temporary = None
        except OSError as exc:
            raise ImpactReportError(
                f"Atomic impact-report replacement failed: {path.name}"
            ) from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
