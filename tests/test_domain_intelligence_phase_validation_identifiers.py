from forge.domain_intelligence.phase_validation.identifiers import (
    phase_validation_check_identifier,
    phase_validation_result_identifier,
)


def test_phase_validation_check_identifier_is_deterministic() -> None:
    first = phase_validation_check_identifier(
        {"phase": "4", "name": "architecture"}
    )
    second = phase_validation_check_identifier(
        {"name": "architecture", "phase": "4"}
    )

    assert first == second
    assert first.startswith("phase-validation-check-")


def test_phase_validation_result_identifier_changes_by_status() -> None:
    passed = phase_validation_result_identifier(
        {"check_id": "check-1", "status": "pass"}
    )
    failed = phase_validation_result_identifier(
        {"check_id": "check-1", "status": "fail"}
    )

    assert passed != failed