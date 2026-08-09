"""Governed repository mutation for M5.9 Package 5."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.execution_policy import authorize_execution
from forge.general_engineering.models import (
    ChangePlan,
    EngineeringRequest,
    GeneratedChangeSet,
)
from forge.general_engineering.safe_edit_adapter import (
    build_safe_edit_request,
)
from forge.safe_code_editing.models import SafeEditReport
from forge.safe_code_editing.service import SafeCodeEditingService


@dataclass(frozen=True)
class EngineeringExecutionResult:
    report: SafeEditReport
    affected_paths: tuple[str, ...]


class EngineeringExecutionService:
    """Execute a validated change set through Safe Code Editing only."""

    def __init__(
        self,
        safe_editing: SafeCodeEditingService | None = None,
    ) -> None:
        self.safe_editing = safe_editing or SafeCodeEditingService()

    def execute(
        self,
        *,
        request: EngineeringRequest,
        plan: ChangePlan,
        change_set: GeneratedChangeSet,
        approved: bool,
        dry_run: bool = True,
    ) -> EngineeringExecutionResult:
        decision = authorize_execution(
            request=request,
            plan=plan,
            change_set=change_set,
            approved=approved,
            dry_run=dry_run,
        )

        safe_request = build_safe_edit_request(
            request=request,
            plan=plan,
            change_set=change_set,
            approved=decision.approved,
            dry_run=decision.dry_run,
        )
        report = self.safe_editing.execute(safe_request)

        return EngineeringExecutionResult(
            report=report,
            affected_paths=decision.affected_paths,
        )


engineering_execution_service = EngineeringExecutionService()