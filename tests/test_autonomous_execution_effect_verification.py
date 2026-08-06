import pytest

from forge.autonomous_execution.effect_verification import (
    verify_affected_files,
)
from forge.autonomous_execution.errors import ToolContractError


def test_files_inside_scope_pass() -> None:
    verify_affected_files(
        (
            "forge/autonomous_execution/tool_gateway.py",
            "forge/autonomous_execution/tool_registry.py",
        ),
        ("forge/autonomous_execution",),
    )


def test_file_outside_scope_is_rejected() -> None:
    with pytest.raises(ToolContractError):
        verify_affected_files(
            ("deployments/production.yml",),
            ("forge/autonomous_execution",),
        )