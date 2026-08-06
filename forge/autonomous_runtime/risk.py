"""Deterministic risk classification for autonomous actions."""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import Final

from forge.autonomous_runtime.states import RiskClass

_ACTION_RISK: dict[str, RiskClass] = {
    "read_file": RiskClass.R0_READ_ONLY,
    "search_repository": RiskClass.R0_READ_ONLY,
    "create_plan": RiskClass.R1_LOW,
    "write_documentation": RiskClass.R1_LOW,
    "modify_tests": RiskClass.R2_MODERATE,
    "apply_patch": RiskClass.R2_MODERATE,
    "modify_public_api": RiskClass.R3_HIGH,
    "modify_authentication": RiskClass.R3_HIGH,
    "modify_financial_logic": RiskClass.R3_HIGH,
    "modify_safety_logic": RiskClass.R3_HIGH,
    "modify_architecture": RiskClass.R3_HIGH,
    "create_commit": RiskClass.R4_CRITICAL,
    "push_branch": RiskClass.R4_CRITICAL,
    "database_migration": RiskClass.R4_CRITICAL,
    "merge_branch": RiskClass.R4_CRITICAL,
    "create_release": RiskClass.R4_CRITICAL,
    "production_control": RiskClass.R5_HUMAN_CONTROLLED,
}

ACTION_RISK: Final[Mapping[str, RiskClass]] = MappingProxyType(
    _ACTION_RISK
)


def classify_action_risk(
    action_kind: str,
    *,
    fallback: RiskClass = RiskClass.R3_HIGH,
) -> RiskClass:
    """Classify action risk conservatively."""
    return ACTION_RISK.get(action_kind, fallback)


def maximum_risk(
    risks: tuple[RiskClass, ...],
) -> RiskClass:
    """Return the highest risk in a collection."""
    return max(risks, default=RiskClass.R0_READ_ONLY)