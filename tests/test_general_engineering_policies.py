import pytest

from forge.general_engineering.errors import EngineeringPolicyError
from forge.general_engineering.policies import (
    EngineeringLimits,
    EngineeringScopePolicy,
    GeneralEngineeringPolicy,
    is_forbidden_path,
)


def test_default_repair_limit_is_bounded_to_three() -> None:
    policy = GeneralEngineeringPolicy()

    assert policy.limits.max_repair_attempts == 3


def test_repair_limit_cannot_exceed_three() -> None:
    with pytest.raises(ValueError):
        EngineeringLimits(max_repair_attempts=4)


def test_forbidden_paths_are_enforced() -> None:
    policy = EngineeringScopePolicy()

    assert is_forbidden_path(".git/config", policy)
    assert is_forbidden_path(".venv/pyvenv.cfg", policy)
    assert not is_forbidden_path("src/service.py", policy)


def test_forbidden_policy_path_cannot_escape_repository() -> None:
    with pytest.raises(EngineeringPolicyError):
        EngineeringScopePolicy(forbidden_paths=("../outside",))