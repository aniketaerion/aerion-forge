"""Deterministic and atomic mission report rendering."""

import json
import os
from pathlib import Path
from typing import Any

from forge.planning.errors import MissionReportError
from forge.planning.models import MissionPlan, MissionPlanChangeSet


class MissionRenderer:
    """Build and write safe deterministic mission reports."""

    def render(
        self,
        plan: MissionPlan,
        changes: MissionPlanChangeSet,
    ) -> dict[str, str]:
        full = plan.model_dump(mode="json")

        summary_keys = (
            "mission_id",
            "target_name",
            "objective",
            "status",
            "planning_confidence",
            "risk_level",
            "scope",
        )
        summary = {
            key: full[key]
            for key in summary_keys
        }

        payloads: dict[str, Any] = {
            "MISSION_PLAN.json": full,
            "MISSION_SUMMARY.json": summary,
            "MISSION_CONTEXT.json": full["context"],
            "MISSION_RISKS.json": {
                "risks": full["risks"],
                "approvals": full["approvals"],
            },
            "MISSION_ASSUMPTIONS.json": full["assumptions"],
            "MISSION_QUESTIONS.json": full["questions"],
            "MISSION_CHANGES.json": changes.model_dump(mode="json"),
        }

        reports = {
            name: (
                json.dumps(
                    payload,
                    indent=2,
                    ensure_ascii=False,
                    sort_keys=True,
                )
                + "\n"
            )
            for name, payload in payloads.items()
        }

        reports["MISSION_PLAN.md"] = self._markdown(
            plan,
            summary=False,
        )
        reports["MISSION_SUMMARY.md"] = self._markdown(
            plan,
            summary=True,
        )

        return reports

    def write(
        self,
        directory: Path,
        reports: dict[str, str],
    ) -> tuple[str, ...]:
        directory.mkdir(parents=True, exist_ok=True)

        staged: list[tuple[Path, Path]] = []

        try:
            for name, content in sorted(reports.items()):
                destination = directory / name
                temporary = destination.with_suffix(
                    destination.suffix + ".tmp"
                )

                with temporary.open(
                    "w",
                    encoding="utf-8",
                    newline="\n",
                ) as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())

                staged.append((temporary, destination))

            for temporary, destination in staged:
                temporary.replace(destination)

        except OSError as exc:
            for temporary, _ in staged:
                temporary.unlink(missing_ok=True)

            raise MissionReportError(
                "Unable to write mission reports."
            ) from exc

        return tuple(sorted(reports))

    def _markdown(
        self,
        plan: MissionPlan,
        summary: bool,
    ) -> str:
        lines = [
            "# Mission Plan",
            "",
            f"Mission ID: `{plan.mission_id}`",
            f"Target: {plan.target_name}",
            (
                "Status: "
                f"{plan.status.value.upper().replace('_', ' ')}"
            ),
            (
                "Planning confidence: "
                f"{plan.planning_confidence.value.upper()}"
            ),
            f"Risk: {plan.risk_level.value.upper()}",
            "",
            "## Objective",
            "",
            plan.objective.statement,
        ]

        if not summary:
            sections: tuple[
                tuple[str, tuple[object, ...], str],
                ...,
            ] = (
                (
                    "Affected Areas",
                    tuple(plan.affected_areas),
                    "canonical_name",
                ),
                (
                    "Workstreams",
                    tuple(plan.workstreams),
                    "name",
                ),
                (
                    "Required Approvals",
                    tuple(plan.approvals),
                    "level",
                ),
                (
                    "Unresolved Questions",
                    tuple(plan.questions),
                    "question",
                ),
            )

            for title, values, attribute in sections:
                lines.extend(("", f"## {title}", ""))

                for item in values:
                    value = getattr(item, attribute)
                    rendered = (
                        value.value
                        if hasattr(value, "value")
                        else str(value)
                    )
                    lines.append(f"- {rendered}")

        return "\n".join(lines).rstrip() + "\n"
