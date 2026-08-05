"""Reporting for M3.7 Build Verification."""

from __future__ import annotations

import json
from pathlib import Path

from forge.build_verification.errors import BuildVerificationReportError
from forge.build_verification.models import (
    BuildVerificationEvidence,
    ReleaseGateDecision,
)


def render_markdown(
    evidence: BuildVerificationEvidence,
    decision: ReleaseGateDecision,
) -> str:
    """Render a concise release-verification report."""
    lines = [
        "# Build Verification Report",
        "",
        f"- Evidence ID: `{evidence.evidence_id}`",
        f"- Request ID: `{evidence.request.request_id}`",
        f"- Source revision: `{evidence.request.source_revision}`",
        f"- Verification status: `{evidence.status.value}`",
        f"- Release decision: `{decision.decision.value}`",
        f"- Repository fingerprint: `{evidence.repository_fingerprint}`",
        "",
        "## Verification Steps",
        "",
    ]

    for result in evidence.step_results:
        lines.extend(
            [
                f"### {result.step_id}",
                "",
                f"- Status: `{result.status.value}`",
                f"- Exit code: `{result.exit_code}`",
                f"- Duration: `{result.duration_seconds:.3f}s`",
                f"- Findings: `{len(result.findings)}`",
                "",
            ]
        )

    lines.extend(["## Decision Reasons", ""])
    lines.extend(f"- {reason}" for reason in decision.reasons)
    lines.append("")

    if decision.blocking_findings:
        lines.extend(["## Blocking Findings", ""])
        lines.extend(
            f"- `{finding_id}`"
            for finding_id in decision.blocking_findings
        )
        lines.append("")

    return "\n".join(lines)


def write_report_bundle(
    evidence: BuildVerificationEvidence,
    decision: ReleaseGateDecision,
    destination: Path,
) -> dict[str, Path]:
    """Write JSON and Markdown release-verification reports."""
    try:
        destination.mkdir(parents=True, exist_ok=True)

        evidence_path = destination / "BUILD_VERIFICATION_EVIDENCE.json"
        decision_path = destination / "RELEASE_GATE_DECISION.json"
        markdown_path = destination / "BUILD_VERIFICATION_REPORT.md"

        evidence_path.write_text(
            json.dumps(
                evidence.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        decision_path.write_text(
            json.dumps(
                decision.model_dump(mode="json"),
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        markdown_path.write_text(
            render_markdown(evidence, decision),
            encoding="utf-8",
        )
    except OSError as exc:
        raise BuildVerificationReportError(
            f"unable to write build verification report bundle: {exc}"
        ) from exc

    return {
        evidence_path.name: evidence_path,
        decision_path.name: decision_path,
        markdown_path.name: markdown_path,
    }