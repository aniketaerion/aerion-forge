"""Enumerations for autonomous planning."""

from enum import StrEnum


class PlanningState(StrEnum):
    CREATED = "created"
    ANALYSING = "analysing"
    GENERATING = "generating"
    VALIDATING = "validating"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    READY = "ready"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PlanningIntent(StrEnum):
    IMPLEMENT_FEATURE = "implement_feature"
    FIX_DEFECT = "fix_defect"
    REFACTOR = "refactor"
    MIGRATE = "migrate"
    VALIDATE = "validate"
    INVESTIGATE = "investigate"
    DOCUMENT = "document"
    RELEASE = "release"


class PlanningRisk(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class StepKind(StrEnum):
    ANALYSIS = "analysis"
    CODE_CHANGE = "code_change"
    TEST = "test"
    VALIDATION = "validation"
    DOCUMENTATION = "documentation"
    APPROVAL = "approval"
    RELEASE = "release"


class DependencyKind(StrEnum):
    REQUIRES = "requires"
    BLOCKS = "blocks"
    ORDERS_AFTER = "orders_after"
    OPTIONAL = "optional"


class ApprovalRequirement(StrEnum):
    NONE = "none"
    PLAN = "plan"
    CODE = "code"
    RELEASE = "release"