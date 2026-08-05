from forge.mission_orchestration.identifiers import (
    checkpoint_identifier,
    mission_identifier,
    stable_identifier,
)


def test_stable_identifier_is_order_independent() -> None:
    assert stable_identifier("x", {"a": 1, "b": 2}) == stable_identifier(
        "x", {"b": 2, "a": 1}
    )


def test_mission_identifier_has_expected_prefix() -> None:
    assert mission_identifier({"objective": "test"}).startswith("mission_")


def test_checkpoint_identifier_changes_with_payload() -> None:
    assert checkpoint_identifier({"x": 1}) != checkpoint_identifier({"x": 2})