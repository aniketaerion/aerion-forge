from forge.safe_code_editing.identifiers import (
    operation_identifier,
    source_fingerprint,
    stable_identifier,
)


def test_source_fingerprint_is_deterministic() -> None:
    assert source_fingerprint("alpha") == source_fingerprint("alpha")
    assert source_fingerprint("alpha") != source_fingerprint("beta")


def test_stable_identifier_is_order_independent_for_mappings() -> None:
    left = stable_identifier("item", {"a": 1, "b": 2})
    right = stable_identifier("item", {"b": 2, "a": 1})
    assert left == right


def test_operation_identifier_has_expected_prefix() -> None:
    assert operation_identifier({"path": "forge/app.py"}).startswith("editop_")