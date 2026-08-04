"""Bounded repair-candidate planning."""

from __future__ import annotations

from collections import defaultdict

from forge.validation_repair.identifiers import repair_candidate_identifier
from forge.validation_repair.models import RepairCandidate, ValidationFinding


def plan_repairs(findings: tuple[ValidationFinding, ...]) -> tuple[RepairCandidate, ...]:
    """Group actionable findings by path into bounded repair candidates."""
    grouped: dict[str, list[ValidationFinding]] = defaultdict(list)
    for finding in findings:
        if finding.path:
            grouped[finding.path].append(finding)

    candidates: list[RepairCandidate] = []
    for path in sorted(grouped):
        items = grouped[path]
        finding_ids = tuple(sorted(item.finding_id for item in items))
        tools = sorted({item.tool.value for item in items})
        objective = (
            f"Repair {len(items)} validation finding(s) in {path} "
            f"reported by {', '.join(tools)}"
        )
        candidates.append(
            RepairCandidate(
                candidate_id=repair_candidate_identifier(
                    {"path": path, "finding_ids": finding_ids, "objective": objective}
                ),
                finding_ids=finding_ids,
                objective=objective,
                target_paths=(path,),
                risk_notes=(
                    "Candidate is bounded to one repository-relative path.",
                    "Apply mode requires explicit approval.",
                ),
            )
        )
    return tuple(candidates)