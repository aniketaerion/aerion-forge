"""Ordered verification pipeline for M3.7 Build Verification."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from forge.build_verification.decision import decide_release
from forge.build_verification.evidence import build_evidence
from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationPolicy,
    BuildVerificationRequest,
    ReleaseGateDecision,
    VerificationStatus,
    VerificationStepResult,
)
from forge.build_verification.policies import validate_request
from forge.build_verification.registry import (
    BuildVerificationProviderRegistry,
)
from forge.build_verification.runner import run_step


class BuildVerificationPipeline:
    """Execute a bounded verification request in declared order."""

    def __init__(
        self,
        policy: BuildVerificationPolicy | None = None,
        registry: BuildVerificationProviderRegistry | None = None,
    ) -> None:
        self.policy = policy or BuildVerificationPolicy()
        self.registry = registry or BuildVerificationProviderRegistry()

    def execute(
        self,
        request: BuildVerificationRequest,
    ) -> tuple[BuildVerificationEvidence, ReleaseGateDecision]:
        """Run all verification steps and return evidence plus decision."""
        validate_request(request, self.policy)

        root = Path(request.repository_root).resolve()
        started_at = datetime.now(UTC)
        results: list[VerificationStepResult] = []

        for step in request.steps:
            result = run_step(
                root,
                step,
                self.policy,
                self.registry,
            )
            results.append(result)

            if (
                step.required
                and result.status is not VerificationStatus.PASSED
            ):
                break

        evidence = build_evidence(
            request,
            tuple(results),
            repository_root=root,
            started_at=started_at,
            completed_at=datetime.now(UTC),
        )
        decision = decide_release(evidence, self.policy)

        return evidence, decision