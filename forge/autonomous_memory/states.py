"""Enumerations for autonomous memory and learning."""

from enum import StrEnum


class MemoryKind(StrEnum):
    REPOSITORY_FACT = "repository_fact"
    ARCHITECTURE_CONSTRAINT = "architecture_constraint"
    BUSINESS_RULE = "business_rule"
    IMPLEMENTATION_DECISION = "implementation_decision"
    VALIDATION_OUTCOME = "validation_outcome"
    EXECUTION_OUTCOME = "execution_outcome"
    FAILURE_PATTERN = "failure_pattern"
    RECOVERY_PATTERN = "recovery_pattern"
    ENGINEERING_LESSON = "engineering_lesson"
    USER_PREFERENCE = "user_preference"
    HYPOTHESIS = "hypothesis"
    NEGATIVE_EVIDENCE = "negative_evidence"


class MemoryStatus(StrEnum):
    ACTIVE = "active"
    SUPERSEDED = "superseded"
    DISPUTED = "disputed"
    EXPIRED = "expired"
    QUARANTINED = "quarantined"


class MemorySourceKind(StrEnum):
    MISSION = "mission"
    SESSION = "session"
    DECISION = "decision"
    EXECUTION = "execution"
    VALIDATION = "validation"
    REPOSITORY = "repository"
    HUMAN_CORRECTION = "human_correction"
    ARCHITECTURE_REVIEW = "architecture_review"


class RetentionClass(StrEnum):
    PERMANENT = "permanent"
    LONG_LIVED = "long_lived"
    PROJECT_LIFETIME = "project_lifetime"
    BOUNDED = "bounded"
    TEMPORARY = "temporary"
    QUARANTINED = "quarantined"


class ApplicabilityKind(StrEnum):
    EXACT_REPOSITORY = "exact_repository"
    MODULE = "module"
    CAPABILITY = "capability"
    BUSINESS_DOMAIN = "business_domain"
    CROSS_PROJECT = "cross_project"