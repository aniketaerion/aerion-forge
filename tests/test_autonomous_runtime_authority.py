from forge.autonomous_runtime.authority import (
    AuthorityRequest,
    evaluate_authority,
)
from forge.autonomous_runtime.models import (
    AutonomousMission,
    MissionRequest,
)
from forge.autonomous_runtime.states import (
    AuthorityLevel,
    RiskClass,
)


def mission() -> AutonomousMission:
    return AutonomousMission(
        mission_id="mission-1",
        request=MissionRequest(
            request_id="request-1",
            objective="Evaluate authority.",
            repository_root="repository",
            requested_authority=AuthorityLevel.A4_COMMIT,
            requested_by="Aerion",
        ),
        granted_authority=AuthorityLevel.A4_COMMIT,
    )


def test_low_risk_modify_is_allowed_without_explicit_approval() -> None:
    result = evaluate_authority(
        mission(),
        AuthorityRequest(
            required_authority=AuthorityLevel.A2_MODIFY,
            risk_class=RiskClass.R2_MODERATE,
        ),
    )

    assert result.allowed
    assert not result.approval_required


def test_commit_requires_explicit_approval() -> None:
    result = evaluate_authority(
        mission(),
        AuthorityRequest(
            required_authority=AuthorityLevel.A4_COMMIT,
            risk_class=RiskClass.R4_CRITICAL,
        ),
    )

    assert result.allowed
    assert result.approval_required