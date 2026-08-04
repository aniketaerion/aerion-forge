from forge.validation_repair.identifiers import (
    repair_candidate_identifier,
    stable_identifier,
    validation_run_identifier,
)


def test_stable_identifier_is_deterministic() -> None:
    assert stable_identifier("x", {"a": 1, "b": 2}) == stable_identifier(
        "x", {"b": 2, "a": 1}
    )


def test_validation_run_identifier_prefix() -> None:
    assert validation_run_identifier({"tool": "ruff"}).startswith("valrun_")


def test_repair_candidate_identifier_changes_with_payload() -> None:
    assert repair_candidate_identifier({"x": 1}) != repair_candidate_identifier({"x": 2})