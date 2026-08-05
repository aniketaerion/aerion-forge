from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from forge.build_verification.models import (
    BuildVerificationEvidence,
    BuildVerificationRequest,
    ReleaseDecision,
    ReleaseGateDecision,
    VerificationStatus,
    VerificationStep,
    VerificationStepResult,
    VerificationTool,
)


def test_step_rejects_repository_escape() -> None:
    with pytest.raises(ValidationError):
        VerificationStep(
            step_id="step-1",
            tool=VerificationTool.RUFF,
            name="Ruff",
            working_directory="../outside",
        )


def test_request_rejects_duplicate_step_ids() -> None:
    step = VerificationStep(
        step_id="step-1",
        tool=VerificationTool.RUFF,
        name="Ruff",
    )
    with pytest.raises(ValidationError):
        BuildVerificationRequest(
            request_id="request-1",
            repository_root=".",
            source_revision="abc",
            objective="verify",
            steps=(step, step),
        )


def test_terminal_step_result_requires_completion_time() -> None:
    with pytest.raises(ValidationError):
        VerificationStepResult(
            step_id="step-1",
            status=VerificationStatus.PASSED,
            exit_code=0,
        )


def test_terminal_evidence_requires_completion_time() -> None:
    step = VerificationStep(
        step_id="step-1",
        tool=VerificationTool.RUFF,
        name="Ruff",
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=".",
        source_revision="abc",
        objective="verify",
        steps=(step,),
    )
    with pytest.raises(ValidationError):
        BuildVerificationEvidence(
            evidence_id="evidence-1",
            request=request,
            status=VerificationStatus.PASSED,
            repository_fingerprint="a" * 64,
            started_at=datetime.now(UTC),
        )


def test_release_decision_requires_reason() -> None:
    with pytest.raises(ValidationError):
        ReleaseGateDecision(
            decision_id="decision-1",
            evidence_id="evidence-1",
            decision=ReleaseDecision.APPROVED,
            reasons=(),
        )