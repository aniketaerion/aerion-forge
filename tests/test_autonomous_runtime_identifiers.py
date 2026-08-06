import pytest

from forge.autonomous_runtime.errors import MissionIdentifierError
from forge.autonomous_runtime.identifiers import (
    deterministic_identifier,
    mission_identifier,
)


def test_deterministic_identifier_is_stable() -> None:
    first = mission_identifier(
        {"objective": "Create mission contracts", "version": 1}
    )
    second = mission_identifier(
        {"version": 1, "objective": "Create mission contracts"}
    )

    assert first == second
    assert first.startswith("mission-")


def test_identifier_rejects_unsupported_values() -> None:
    with pytest.raises(MissionIdentifierError):
        deterministic_identifier(
            "mission",
            {"unsupported": object()},
        )