"""Deterministic Execution Controller builders."""

from collections import Counter
from collections.abc import Mapping, Sequence

from forge.execution_controller.identifiers import (
    approval_id,
    evidence_id,
    execution_request_fingerprint,
    execution_request_id,
    operation_id,
    session_fingerprint,
    session_id,
    transition_id,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    EvidenceType,
    ExecutionEvent,
    ExecutionEvidence,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionSession,
    ExecutionState,
    ExecutionStatistics,
    ExecutionTransition,
    OperationStatus,
)
from forge.execution_controller.policies import (
    resolve_next_state,
)


class ExecutionControllerBuilder:
    """Build immutable deterministic execution artifacts."""

    def build_request(
        self,
        *,
        mission_id: str,
        task_ids: Sequence[str],
        requested_operations: Sequence[str],
        dry_run: bool,
        source_fingerprints: Mapping[str, str],
    ) -> ExecutionRequest:
        request_identity = execution_request_id(
            mission_id,
            task_ids,
            requested_operations,
            dry_run,
            source_fingerprints,
        )

        placeholder = ExecutionRequest(
            request_id=request_identity,
            request_fingerprint="pending",
            mission_id=mission_id,
            task_ids=tuple(task_ids),
            requested_operations=tuple(requested_operations),
            dry_run=dry_run,
            source_fingerprints=source_fingerprints,
        )

        return ExecutionRequest(
            **placeholder.model_dump(exclude={"request_fingerprint"}),
            request_fingerprint=(execution_request_fingerprint(placeholder)),
        )

    def build_approval(
        self,
        request: ExecutionRequest,
        *,
        approver_id: str,
        decision: ApprovalDecision,
        approved_operations: Sequence[str],
        evidence_reference: str,
    ) -> ApprovalRecord:
        operations = tuple(approved_operations) if decision is ApprovalDecision.APPROVED else ()

        return ApprovalRecord(
            approval_id=approval_id(
                request.request_fingerprint,
                approver_id,
                operations,
                evidence_reference,
            ),
            request_fingerprint=(request.request_fingerprint),
            approver_id=approver_id,
            decision=decision,
            approved_operations=operations,
            evidence_reference=evidence_reference,
        )

    def build_operation(
        self,
        request: ExecutionRequest,
        *,
        task_id: str,
        tool_id: str,
        operation_type: str,
        arguments_fingerprint: str,
        status: OperationStatus = (OperationStatus.PENDING),
        result_reference: str | None = None,
        failure_reference: str | None = None,
    ) -> ExecutionOperation:
        return ExecutionOperation(
            operation_id=operation_id(
                request.request_id,
                task_id,
                tool_id,
                operation_type,
                arguments_fingerprint,
            ),
            task_id=task_id,
            tool_id=tool_id,
            operation_type=operation_type,
            arguments_fingerprint=(arguments_fingerprint),
            status=status,
            result_reference=result_reference,
            failure_reference=failure_reference,
        )

    def build_evidence(
        self,
        *,
        session_id_value: str,
        evidence_type: EvidenceType,
        source: str,
        fingerprint: str,
        reference: str,
        metadata: Mapping[str, str] | None = None,
    ) -> ExecutionEvidence:
        placeholder = ExecutionEvidence(
            evidence_id="pending",
            evidence_type=evidence_type,
            source=source,
            fingerprint=fingerprint,
            reference=reference,
            metadata=metadata or {},
        )

        return ExecutionEvidence(
            **placeholder.model_dump(exclude={"evidence_id"}),
            evidence_id=evidence_id(
                session_id_value,
                placeholder,
            ),
        )

    def build_transition(
        self,
        *,
        session_id_value: str,
        current_state: ExecutionState,
        event: ExecutionEvent,
        ordinal: int,
        reason: str | None = None,
        evidence_ids: Sequence[str] = (),
    ) -> ExecutionTransition:
        next_state = resolve_next_state(
            current_state,
            event,
        )

        placeholder = ExecutionTransition(
            transition_id="pending",
            previous_state=current_state,
            event=event,
            next_state=next_state,
            reason=reason,
            evidence_ids=tuple(evidence_ids),
        )

        return ExecutionTransition(
            **placeholder.model_dump(exclude={"transition_id"}),
            transition_id=transition_id(
                session_id_value,
                placeholder,
                ordinal,
            ),
        )

    def build_session(
        self,
        request: ExecutionRequest,
        *,
        approval: ApprovalRecord | None = None,
        current_state: ExecutionState = (ExecutionState.REQUESTED),
        transitions: Sequence[ExecutionTransition] = (),
        operations: Sequence[ExecutionOperation] = (),
        evidence: Sequence[ExecutionEvidence] = (),
        source_fingerprints: (Mapping[str, str] | None) = None,
    ) -> ExecutionSession:
        session_identity = session_id(
            request,
            approval,
        )

        placeholder = ExecutionSession(
            session_id=session_identity,
            session_fingerprint="pending",
            request=request,
            approval=approval,
            current_state=current_state,
            transitions=tuple(transitions),
            operations=tuple(operations),
            evidence=tuple(evidence),
            statistics=self._statistics(operations),
            source_fingerprints=(
                source_fingerprints
                if source_fingerprints is not None
                else request.source_fingerprints
            ),
        )

        return ExecutionSession(
            **placeholder.model_dump(exclude={"session_fingerprint"}),
            session_fingerprint=session_fingerprint(placeholder),
        )

    def transition_session(
        self,
        session: ExecutionSession,
        event: ExecutionEvent,
        *,
        reason: str | None = None,
        evidence_ids: Sequence[str] = (),
    ) -> ExecutionSession:
        transition = self.build_transition(
            session_id_value=session.session_id,
            current_state=session.current_state,
            event=event,
            ordinal=len(session.transitions) + 1,
            reason=reason,
            evidence_ids=evidence_ids,
        )

        return self.build_session(
            session.request,
            approval=session.approval,
            current_state=transition.next_state,
            transitions=(
                *session.transitions,
                transition,
            ),
            operations=session.operations,
            evidence=session.evidence,
            source_fingerprints=(session.source_fingerprints),
        )

    def replace_operations(
        self,
        session: ExecutionSession,
        operations: Sequence[ExecutionOperation],
    ) -> ExecutionSession:
        return self.build_session(
            session.request,
            approval=session.approval,
            current_state=session.current_state,
            transitions=session.transitions,
            operations=operations,
            evidence=session.evidence,
            source_fingerprints=(session.source_fingerprints),
        )

    def append_evidence(
        self,
        session: ExecutionSession,
        evidence: ExecutionEvidence,
    ) -> ExecutionSession:
        return self.build_session(
            session.request,
            approval=session.approval,
            current_state=session.current_state,
            transitions=session.transitions,
            operations=session.operations,
            evidence=(
                *session.evidence,
                evidence,
            ),
            source_fingerprints=(session.source_fingerprints),
        )

    def _statistics(
        self,
        operations: Sequence[ExecutionOperation],
    ) -> ExecutionStatistics:
        counts = Counter(operation.status for operation in operations)

        return ExecutionStatistics(
            operation_count=len(operations),
            pending_count=(
                counts[OperationStatus.PENDING]
                + counts[OperationStatus.APPROVED]
                + counts[OperationStatus.QUEUED]
            ),
            running_count=counts[OperationStatus.RUNNING],
            succeeded_count=counts[OperationStatus.SUCCEEDED],
            failed_count=counts[OperationStatus.FAILED],
            blocked_count=counts[OperationStatus.BLOCKED],
            cancelled_count=counts[OperationStatus.CANCELLED],
        )
