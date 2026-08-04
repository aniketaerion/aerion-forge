from forge.autonomous_repair.identifiers import (
    patch_identifier,
    proposal_identifier,
    stable_identifier,
)


def test_stable_identifier_is_order_independent() -> None:
    assert stable_identifier("x", {"a": 1, "b": 2}) == stable_identifier(
        "x", {"b": 2, "a": 1}
    )


def test_proposal_identifier_has_expected_prefix() -> None:
    assert proposal_identifier({"candidate": "c1"}).startswith("repairprop_")


def test_patch_identifier_changes_with_payload() -> None:
    assert patch_identifier({"x": 1}) != patch_identifier({"x": 2})