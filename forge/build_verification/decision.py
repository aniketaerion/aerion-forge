"""Release-gate decision engine for M3.7 Build Verification."""

from __future__ import annotations

from forge.build_verification.identifiers import (
    release_decision_identifier,
)
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    ReleaseDecision,
    ReleaseGateDecision,
    VerificationStatus,
)
from forge.build_verification.policies import blocking_finding_ids


def decide_release(
    evidence: BuildVerificationEvidence,
    policy: BuildVerificationPolicy,
) -> ReleaseGateDecision:
    """Create a deterministic release decision from evidence."""
    findings = tuple(
        finding
        for result in evidence.step_results
        for finding in result.findings
    )
    blocking = blocking_finding_ids(findings, policy)

    required_steps = {
        step.step_id
        for step in evidence.request.steps
        if step.required
    }
    passed_steps = {
        result.step_id
        for result in evidence.step_results
        if result.status is VerificationStatus.PASSED
    }
    missing_required = tuple(sorted(required_steps - passed_steps))

    reasons: list[str] = []

    if evidence.status is not VerificationStatus.PASSED:
        reasons.append(
            f"verification evidence status is {evidence.status.value}"
        )

    if missing_required:
        reasons.append(
            "required verification steps did not pass: "
            + ", ".join(missing_required)
        )

    if blocking:
        reasons.append(
            "blocking verification findings exist: "
            + ", ".join(blocking)
        )

    if reasons:
        decision = ReleaseDecision.REJECTED
    elif not evidence.step_results:
        decision = ReleaseDecision.MANUAL_REVIEW
        reasons.append("verification evidence contains no step results")
    else:
        decision = ReleaseDecision.APPROVED
        reasons.append("all required verification gates passed")

    decision_id = release_decision_identifier(
        {
            "evidence_id": evidence.evidence_id,
            "decision": decision.value,
            "reasons": reasons,
            "blocking_findings": blocking,
        }
    )

    return ReleaseGateDecision(
        decision_id=decision_id,
        evidence_id=evidence.evidence_id,
        decision=decision,
        reasons=tuple(reasons),
        blocking_findings=blocking,
    )