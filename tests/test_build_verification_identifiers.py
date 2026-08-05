from forge.build_verification.identifiers import (
    release_decision_identifier,
    stable_identifier,
    verification_request_identifier,
)


def test_stable_identifier_is_deterministic() -> None:
    first = stable_identifier(
        "sample",
        {"paths": ["b.py", "a.py"], "revision": "abc"},
    )
    second = stable_identifier(
        "sample",
        {"revision": "abc", "paths": ["b.py", "a.py"]},
    )
    assert first == second
    assert first.startswith("sample-")


def test_request_identifier_changes_with_revision() -> None:
    first = verification_request_identifier(
        {"revision": "abc", "objective": "verify"}
    )
    second = verification_request_identifier(
        {"revision": "def", "objective": "verify"}
    )
    assert first != second


def test_release_decision_identifier_has_expected_prefix() -> None:
    identifier = release_decision_identifier(
        {"evidence_id": "evidence-1", "decision": "approved"}
    )
    assert identifier.startswith("release-decision-")