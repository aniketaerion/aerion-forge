"""Execution Controller orchestration service."""

from collections.abc import Mapping, Sequence
from pathlib import Path

from forge.execution_controller.builder import (
    ExecutionControllerBuilder,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    EvidenceType,
    ExecutionControllerConfiguration,
    ExecutionEvent,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionSession,
    ExecutionState,
    ExecutionValidationResult,
)
from forge.execution_controller.renderer import (
    ExecutionControllerRenderer,
)
from forge.execution_controller.validator import (
    ExecutionControllerValidator,
)


class ExecutionControllerService:
    """Coordinate validated execution-controller operations."""

    def __init__(
        self,
        *,
        configuration: (ExecutionControllerConfiguration | None) = None,
        builder: ExecutionControllerBuilder | None = None,
        validator: ExecutionControllerValidator | None = None,
        renderer: ExecutionControllerRenderer | None = None,
    ) -> None:
        self.configuration = configuration or ExecutionControllerConfiguration()
        self.builder = builder or ExecutionControllerBuilder()
        self.validator = validator or ExecutionControllerValidator()
        self.renderer = renderer or ExecutionControllerRenderer()

    def create_request(
        self,
        *,
        mission_id: str,
        task_ids: Sequence[str],
        requested_operations: Sequence[str],
        dry_run: bool,
        source_fingerprints: Mapping[str, str],
    ) -> ExecutionRequest:
        return self.builder.build_request(
            mission_id=mission_id,
            task_ids=task_ids,
            requested_operations=requested_operations,
            dry_run=dry_run,
            source_fingerprints=source_fingerprints,
        )

    def validate_request(
        self,
        request: ExecutionRequest,
        *,
        known_mission_id: str,
        known_task_ids: Sequence[str],
        required_source_fingerprints: Mapping[str, str],
    ) -> ExecutionValidationResult:
        return self.validator.validate_request(
            request,
            self.configuration,
            known_mission_id=known_mission_id,
            known_task_ids=known_task_ids,
            required_source_fingerprints=dict(required_source_fingerprints),
        )

    def validate_request_or_raise(
        self,
        request: ExecutionRequest,
        *,
        known_mission_id: str,
        known_task_ids: Sequence[str],
        required_source_fingerprints: Mapping[str, str],
    ) -> ExecutionValidationResult:
        result = self.validate_request(
            request,
            known_mission_id=known_mission_id,
            known_task_ids=known_task_ids,
            required_source_fingerprints=(required_source_fingerprints),
        )

        return self.validator.validate_or_raise(result)

    def record_approval(
        self,
        request: ExecutionRequest,
        *,
        approver_id: str,
        decision: ApprovalDecision,
        approved_operations: Sequence[str],
        evidence_reference: str,
    ) -> ApprovalRecord:
        approval = self.builder.build_approval(
            request,
            approver_id=approver_id,
            decision=decision,
            approved_operations=approved_operations,
            evidence_reference=evidence_reference,
        )

        result = self.validator.validate_approval_record(
            request,
            approval,
            self.configuration,
        )
        self.validator.validate_or_raise(result)

        return approval

    def create_session(
        self,
        request: ExecutionRequest,
        *,
        approval: ApprovalRecord | None = None,
        source_fingerprints: (Mapping[str, str] | None) = None,
    ) -> ExecutionSession:
        if approval is not None:
            result = self.validator.validate_approval_record(
                request,
                approval,
                self.configuration,
            )
            self.validator.validate_or_raise(result)

        initial_state = (
            ExecutionState.APPROVED if approval is not None else ExecutionState.REQUESTED
        )

        return self.builder.build_session(
            request,
            approval=approval,
            current_state=initial_state,
            source_fingerprints=source_fingerprints,
        )

    def transition_session(
        self,
        session: ExecutionSession,
        event: ExecutionEvent,
        *,
        reason: str | None = None,
        evidence_ids: Sequence[str] = (),
    ) -> ExecutionSession:
        updated = self.builder.transition_session(
            session,
            event,
            reason=reason,
            evidence_ids=evidence_ids,
        )

        result = self.validator.validate_session(
            updated,
            self.configuration,
        )
        self.validator.validate_or_raise(result)

        return updated

    def add_operation(
        self,
        session: ExecutionSession,
        operation: ExecutionOperation,
        *,
        registered_tools: frozenset[str],
    ) -> ExecutionSession:
        if session.approval is None:
            result = self.validator.validate_approval_record(
                session.request,
                None,
                self.configuration,
            )
            self.validator.validate_or_raise(result)

            raise AssertionError("Approval validation unexpectedly passed.")

        operation_result = self.validator.validate_operation(
            session.request,
            session.approval,
            operation,
            registered_tools,
        )
        self.validator.validate_or_raise(operation_result)

        return self.builder.replace_operations(
            session,
            (
                *session.operations,
                operation,
            ),
        )

    def add_evidence(
        self,
        session: ExecutionSession,
        *,
        evidence_type: EvidenceType,
        source: str,
        fingerprint: str,
        reference: str,
        metadata: Mapping[str, str] | None = None,
    ) -> ExecutionSession:
        evidence = self.builder.build_evidence(
            session_id_value=session.session_id,
            evidence_type=evidence_type,
            source=source,
            fingerprint=fingerprint,
            reference=reference,
            metadata=metadata,
        )

        return self.builder.append_evidence(
            session,
            evidence,
        )

    def replace_operations(
        self,
        session: ExecutionSession,
        operations: Sequence[ExecutionOperation],
    ) -> ExecutionSession:
        return self.builder.replace_operations(
            session,
            operations,
        )

    def validate_session(
        self,
        session: ExecutionSession,
    ) -> ExecutionValidationResult:
        return self.validator.validate_session(
            session,
            self.configuration,
        )

    def validate_session_or_raise(
        self,
        session: ExecutionSession,
    ) -> ExecutionValidationResult:
        result = self.validate_session(session)

        return self.validator.validate_or_raise(result)

    def render_reports(
        self,
        session: ExecutionSession,
    ) -> Mapping[str, str]:
        self.validate_session_or_raise(session)

        return self.renderer.render_suite(session)

    def write_reports(
        self,
        session: ExecutionSession,
        reports_path: Path,
    ) -> tuple[str, ...]:
        self.validate_session_or_raise(session)

        return self.renderer.write_suite(
            session,
            reports_path,
        )
