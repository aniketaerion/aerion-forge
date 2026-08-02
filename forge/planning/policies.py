"""Explicit Milestone 2.1 planning policies and boundaries."""

from enum import StrEnum


class PlanningPolicy(StrEnum):
    PRESERVE_ARCHITECTURE = "preserve_architecture_by_default"
    REQUIRE_VALID_TARGET = "require_valid_target"
    REQUIRE_RUNTIME_READINESS = "require_runtime_readiness"
    REQUIRE_CURRENT_STATE = "require_current_project_state"
    ALLOW_DEGRADED = "allow_degraded_runtime_with_conditions"
    RECORD_UNKNOWN = "record_unknown_context"
    APPROVE_HIGH_RISK = "require_approval_for_high_risk"
    NEVER_EXECUTE = "never_execute_during_planning"
    NEVER_EDIT = "never_edit_during_planning"
    NEVER_INVENT_FILES = "never_invent_files"
    NEVER_CLAIM_SEMANTICS = "never_claim_source_semantics"
    NEVER_HIDE_ASSUMPTIONS = "never_hide_assumptions"


POLICY_VERSION = "2.1.0"
MILESTONE_EXCLUSIONS = (
    "automatic remediation",
    "database migration execution",
    "deployment",
    "Git mutation",
    "patch generation",
    "source-code modification",
    "target build execution",
    "target test execution",
)
