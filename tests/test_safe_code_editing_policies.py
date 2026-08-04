from pathlib import Path

import pytest

from forge.safe_code_editing.errors import (
    ApprovalRequiredError,
    InvalidEditPathError,
)
from forge.safe_code_editing.policies import SafeEditPolicy


def test_policy_defaults_are_safe() -> None:
    policy = SafeEditPolicy()
    assert policy.dry_run_default is True
    assert policy.require_explicit_approval is True
    assert "utf-8" in policy.allowed_encodings


def test_policy_rejects_unapproved_apply() -> None:
    policy = SafeEditPolicy()
    with pytest.raises(ApprovalRequiredError):
        policy.validate_apply_mode(dry_run=False, approved=False)


def test_policy_rejects_protected_path() -> None:
    policy = SafeEditPolicy()
    with pytest.raises(InvalidEditPathError):
        policy.validate_relative_path(".git/config")


def test_policy_resolves_repository_path(tmp_path: Path) -> None:
    policy = SafeEditPolicy()
    resolved = policy.resolve_path(tmp_path, "forge/app.py")
    assert resolved == (tmp_path / "forge/app.py").resolve()