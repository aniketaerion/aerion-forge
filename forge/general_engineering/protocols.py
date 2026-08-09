"""Provider protocols for the M5.9 General Engineering Agent."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from forge.general_engineering.models import (
    ChangePlan,
    ChangeSpecification,
    EngineeringContext,
    EngineeringRequest,
    GeneratedChangeSet,
    RepairProposal,
    ValidationOutcome,
)


@runtime_checkable
class EngineeringProvider(Protocol):
    """Reasoning-only provider boundary.

    Implementations propose typed engineering artifacts. They are intentionally
    not given repository mutation or shell-execution methods.
    """

    def understand_request(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
    ) -> ChangeSpecification:
        """Normalize the engineering request against repository context."""

    def propose_change_plan(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        specification: ChangeSpecification,
    ) -> ChangePlan:
        """Propose a structured, repository-grounded change plan."""

    def synthesize_edits(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
    ) -> GeneratedChangeSet:
        """Propose structured edit operations for an approved plan."""

    def propose_repair(
        self,
        request: EngineeringRequest,
        context: EngineeringContext,
        plan: ChangePlan,
        validation_outcome: ValidationOutcome,
        attempt_number: int,
    ) -> RepairProposal:
        """Propose a bounded repair from validation evidence."""