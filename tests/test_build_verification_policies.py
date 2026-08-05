from pathlib import Path

import pytest

from forge.build_verification.errors import BuildVerificationPolicyError
from forge.build_verification.models import (
    BuildVerificationPolicy,
    BuildVerificationRequest,
    FindingSeverity,
    VerificationFinding,
    VerificationStep,
    VerificationTool,
)
from forge.build_verification.policies import (
    blocking_finding_ids,
    validate_request,
    validate_target_paths,
)


def test_policy_rejects_network_step() -> None:
    step = VerificationStep(
        step_id="step-1",
        tool=VerificationTool.PYTEST,
        name="Pytest",
        allow_network=True,
    )
    request = BuildVerificationRequest(
        request_id="request-1",
        repository_root=".",
        source_revision="abc",
        objective="verify",
        steps=(step,),
    )
    with pytest.raises(BuildVerificationPolicyError):
        validate_request(request, BuildVerificationPolicy())


def test_target_paths_are_normalized(tmp_path: Path) -> None:
    (tmp_path / "forge").mkdir()
    normalized = validate_target_paths(tmp_path, ("forge", "forge"))
    assert normalized == ("forge",)


def test_high_finding_blocks_release() -> None:
    finding = VerificationFinding(
        finding_id="finding-1",
        step_id="step-1",
        severity=FindingSeverity.HIGH,
        code="TEST",
        message="blocking issue",
    )
    assert blocking_finding_ids(
        (finding,),
        BuildVerificationPolicy(),
    ) == ("finding-1",)