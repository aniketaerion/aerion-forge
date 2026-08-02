"""Deterministic rendering for Safe Change Planning artifacts."""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from forge.safe_change_planning.errors import (
    ChangePlanningReportError,
)
from forge.safe_change_planning.models import (
    SafeChangePlan,
)

SAFE_CHANGE_PLAN_JSON: Final = "SAFE_CHANGE_PLAN.json"
SAFE_CHANGE_SUMMARY_JSON: Final = "SAFE_CHANGE_SUMMARY.json"
SAFE_CHANGE_TARGETS_JSON: Final = "SAFE_CHANGE_TARGETS.json"
SAFE_CHANGE_RISKS_JSON: Final = "SAFE_CHANGE_RISKS.json"
SAFE_CHANGE_VERIFICATION_JSON: Final = "SAFE_CHANGE_VERIFICATION.json"
SAFE_CHANGE_ROLLBACK_JSON: Final = "SAFE_CHANGE_ROLLBACK.json"
SAFE_CHANGE_TRACEABILITY_JSON: Final = "SAFE_CHANGE_TRACEABILITY.json"
SAFE_CHANGE_PLAN_MARKDOWN: Final = "SAFE_CHANGE_PLAN.md"

SAFE_CHANGE_REPORT_NAMES: Final[tuple[str, ...]] = (
    SAFE_CHANGE_PLAN_JSON,
    SAFE_CHANGE_SUMMARY_JSON,
    SAFE_CHANGE_TARGETS_JSON,
    SAFE_CHANGE_RISKS_JSON,
    SAFE_CHANGE_VERIFICATION_JSON,
    SAFE_CHANGE_ROLLBACK_JSON,
    SAFE_CHANGE_TRACEABILITY_JSON,
    SAFE_CHANGE_PLAN_MARKDOWN,
)


def _canonical_json(
    value: object,
) -> str:
    """Return stable human-readable canonical JSON."""

    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n"
    )


class SafeChangePlanningRenderer:
    """Render and atomically persist Safe Change Planning reports."""

    def render_plan_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render the complete Safe Change Plan."""

        return _canonical_json(plan.model_dump(mode="json"))

    def render_summary_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render compact planning summary information."""

        payload = {
            "schema_version": plan.schema_version,
            "plan_id": plan.plan_id,
            "plan_fingerprint": plan.plan_fingerprint,
            "request_id": plan.request.request_id,
            "request_fingerprint": (plan.request.request_fingerprint),
            "mission_id": plan.request.mission_id,
            "task_ids": list(plan.request.task_ids),
            "objective": plan.request.objective,
            "risk_level": (plan.risk_assessment.risk_level.value),
            "risk_score": plan.risk_assessment.score,
            "approval_required": (plan.risk_assessment.approval_required),
            "statistics": plan.statistics.model_dump(mode="json"),
        }

        return _canonical_json(payload)

    def render_targets_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render targets, actions, phases, and dependencies."""

        payload = {
            "plan_id": plan.plan_id,
            "targets": [target.model_dump(mode="json") for target in plan.targets],
            "actions": [action.model_dump(mode="json") for action in plan.actions],
            "dependencies": [
                dependency.model_dump(mode="json") for dependency in plan.dependencies
            ],
            "phases": [phase.model_dump(mode="json") for phase in plan.phases],
        }

        return _canonical_json(payload)

    def render_risks_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render the deterministic risk assessment."""

        payload = {
            "plan_id": plan.plan_id,
            "assessment": (plan.risk_assessment.model_dump(mode="json")),
        }

        return _canonical_json(payload)

    def render_verification_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render planned verification activities."""

        payload = {
            "plan_id": plan.plan_id,
            "verification_steps": [
                step.model_dump(mode="json") for step in plan.verification_steps
            ],
            "required_step_count": sum(step.required for step in plan.verification_steps),
        }

        return _canonical_json(payload)

    def render_rollback_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render rollback and compensation activities."""

        payload = {
            "plan_id": plan.plan_id,
            "rollback_steps": [step.model_dump(mode="json") for step in plan.rollback_steps],
            "irreversible_step_count": sum(step.irreversible for step in plan.rollback_steps),
        }

        return _canonical_json(payload)

    def render_traceability_json(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render source and cross-artifact traceability."""

        payload = {
            "plan_id": plan.plan_id,
            "request": {
                "request_id": plan.request.request_id,
                "mission_id": plan.request.mission_id,
                "task_ids": list(plan.request.task_ids),
                "source_fingerprints": dict(plan.request.source_fingerprints),
            },
            "plan_source_fingerprints": dict(plan.source_fingerprints),
            "target_traceability": [
                {
                    "target_id": target.target_id,
                    "source_ids": list(target.source_ids),
                }
                for target in plan.targets
            ],
            "action_traceability": [
                {
                    "action_id": action.action_id,
                    "target_id": action.target_id,
                    "prerequisites": list(action.prerequisites),
                    "verification_step_ids": list(action.verification_step_ids),
                    "rollback_step_ids": list(action.rollback_step_ids),
                }
                for action in plan.actions
            ],
        }

        return _canonical_json(payload)

    def render_markdown(
        self,
        plan: SafeChangePlan,
    ) -> str:
        """Render the complete human-readable planning report."""

        lines: list[str] = [
            "# Safe Change Plan",
            "",
            "## Plan identity",
            "",
            f"- Plan ID: `{plan.plan_id}`",
            (f"- Plan fingerprint: `{plan.plan_fingerprint}`"),
            (f"- Request ID: `{plan.request.request_id}`"),
            (f"- Mission ID: `{plan.request.mission_id}`"),
            "",
            "## Objective",
            "",
            plan.request.objective,
            "",
            "## Scope summary",
            "",
            (f"- Targets: {plan.statistics.target_count}"),
            (f"- Actions: {plan.statistics.action_count}"),
            (f"- Dependencies: {plan.statistics.dependency_count}"),
            (f"- Verification steps: {plan.statistics.verification_count}"),
            (f"- Rollback steps: {plan.statistics.rollback_count}"),
            (f"- Planning phases: {plan.statistics.phase_count}"),
            "",
            "## Risk assessment",
            "",
            (f"- Risk level: **{plan.risk_assessment.risk_level.value}**"),
            (f"- Risk score: {plan.risk_assessment.score}"),
            (f"- Approval required: {'Yes' if plan.risk_assessment.approval_required else 'No'}"),
            "",
        ]

        if plan.risk_assessment.factors:
            lines.extend(
                [
                    "### Risk factors",
                    "",
                ]
            )

            for factor in plan.risk_assessment.factors:
                lines.append(f"- **{factor.factor_type.value}** ({factor.score}): {factor.reason}")

                if factor.mitigation:
                    lines.append(f"  - Mitigation: {factor.mitigation}")

            lines.append("")

        if plan.risk_assessment.mitigations:
            lines.extend(
                [
                    "### Required mitigations",
                    "",
                ]
            )

            for mitigation in plan.risk_assessment.mitigations:
                lines.append(f"- {mitigation}")

            lines.append("")

        lines.extend(
            [
                "## Change targets",
                "",
            ]
        )

        if not plan.targets:
            lines.extend(
                [
                    "No targets declared.",
                    "",
                ]
            )
        else:
            for target in plan.targets:
                lines.extend(
                    [
                        (f"### `{target.path}`"),
                        "",
                        (f"- Target ID: `{target.target_id}`"),
                        (f"- Type: {target.target_type.value}"),
                        (f"- Component: {target.component}"),
                        f"- Reason: {target.reason}",
                        "",
                    ]
                )

        lines.extend(
            [
                "## Ordered implementation phases",
                "",
            ]
        )

        actions_by_id = {action.action_id: action for action in plan.actions}

        for phase in plan.phases:
            lines.extend(
                [
                    (f"### {phase.sequence}. {phase.title}"),
                    "",
                    (f"Phase type: `{phase.phase_type.value}`"),
                    "",
                ]
            )

            if not phase.action_ids:
                lines.extend(
                    [
                        "No actions declared.",
                        "",
                    ]
                )
                continue

            for action_id in phase.action_ids:
                action = actions_by_id.get(action_id)

                if action is None:
                    lines.append(f"- Missing action reference: `{action_id}`")
                    continue

                lines.append(
                    f"- `{action.action_id}` — **{action.action_type.value}**: {action.description}"
                )

            lines.append("")

        lines.extend(
            [
                "## Verification plan",
                "",
            ]
        )

        if not plan.verification_steps:
            lines.extend(
                [
                    "No verification steps declared.",
                    "",
                ]
            )
        else:
            for verification_step in plan.verification_steps:
                lines.append(
                    
                        f"- `{verification_step.step_id}` - "
                        f"**{verification_step.verification_type.value}**: "
                        f"{verification_step.description}"
                    
                )

                if verification_step.command:
                    lines.append(f"  - Command: `{verification_step.command}`")

            lines.append("")

        lines.extend(
            [
                "## Rollback plan",
                "",
            ]
        )

        if not plan.rollback_steps:
            lines.extend(
                [
                    "No rollback steps declared.",
                    "",
                ]
            )
        else:
            for rollback_step in plan.rollback_steps:
                lines.append(f"- `{rollback_step.step_id}` — {rollback_step.description}")

                if rollback_step.irreversible:
                    lines.append("  - Irreversible: Yes")

                if rollback_step.limitation:
                    lines.append(f"  - Limitation: {rollback_step.limitation}")

            lines.append("")

        lines.extend(
            [
                "## Source traceability",
                "",
            ]
        )

        for key, value in sorted(plan.source_fingerprints.items()):
            lines.append(f"- `{key}`: `{value}`")

        lines.extend(
            [
                "",
                "## Safety boundary",
                "",
                (
                    "This artifact is a read-only change plan. "
                    "It does not modify source code, execute tools, "
                    "run tests, mutate Git, apply migrations, or "
                    "perform deployment."
                ),
                "",
            ]
        )

        return "\n".join(lines)

    def render_suite(
        self,
        plan: SafeChangePlan,
    ) -> Mapping[str, str]:
        """Render the complete deterministic report suite."""

        return {
            SAFE_CHANGE_PLAN_JSON: (self.render_plan_json(plan)),
            SAFE_CHANGE_SUMMARY_JSON: (self.render_summary_json(plan)),
            SAFE_CHANGE_TARGETS_JSON: (self.render_targets_json(plan)),
            SAFE_CHANGE_RISKS_JSON: (self.render_risks_json(plan)),
            SAFE_CHANGE_VERIFICATION_JSON: (self.render_verification_json(plan)),
            SAFE_CHANGE_ROLLBACK_JSON: (self.render_rollback_json(plan)),
            SAFE_CHANGE_TRACEABILITY_JSON: (self.render_traceability_json(plan)),
            SAFE_CHANGE_PLAN_MARKDOWN: (self.render_markdown(plan)),
        }

    def write_suite(
        self,
        plan: SafeChangePlan,
        reports_path: Path,
    ) -> tuple[str, ...]:
        """Atomically persist the complete report suite."""

        suite = self.render_suite(plan)

        try:
            reports_path.mkdir(
                parents=True,
                exist_ok=True,
            )
        except OSError as exc:
            raise ChangePlanningReportError(
                f"Could not create Safe Change Planning report directory: {reports_path}"
            ) from exc

        temporary_paths: list[Path] = []

        try:
            for name, content in suite.items():
                destination = reports_path / name
                temporary = reports_path / (f"{name}.tmp")
                temporary_paths.append(temporary)

                temporary.write_text(
                    content,
                    encoding="utf-8",
                    newline="\n",
                )

                temporary.replace(destination)

        except OSError as exc:
            self._clean_temporary_files(temporary_paths)

            raise ChangePlanningReportError(
                "Could not persist Safe Change Planning report suite."
            ) from exc

        self._clean_temporary_files(temporary_paths)

        return tuple(sorted(suite))

    def _clean_temporary_files(
        self,
        paths: list[Path],
    ) -> None:
        for path in paths:
            try:
                if path.exists():
                    path.unlink()
            except OSError:
                continue
