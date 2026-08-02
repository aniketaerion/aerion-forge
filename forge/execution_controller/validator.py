"""Execution Controller request, approval, and session validation."""

from collections.abc import Iterable

from forge.execution_controller.errors import (
    ExecutionConfigurationError,
    ExecutionValidationError,
)
from forge.execution_controller.models import (
    ApprovalDecision,
    ApprovalRecord,
    ExecutionControllerConfiguration,
    ExecutionOperation,
    ExecutionRequest,
    ExecutionSession,
    ExecutionState,
    ExecutionValidationFinding,
    ExecutionValidationResult,
)
from forge.execution_controller.policies import (
    is_terminal_state,
    validate_approval,
    validate_operation_scope,
    validate_registered_tool,
)


class ExecutionControllerValidator:
    """Validate execution lineage, approval, scope, and state."""

    def validate_request(
        self,
        request: ExecutionRequest,
        configuration: ExecutionControllerConfiguration,
        *,
        known_mission_id: str,
        known_task_ids: Iterable[str],
        required_source_fingerprints: dict[str, str],
    ) -> ExecutionValidationResult:
        findings: list[ExecutionValidationFinding] = []

        if not configuration.enabled:
            raise ExecutionConfigurationError("Execution Controller is disabled.")

        if request.mission_id != known_mission_id:
            findings.append(
                self._error(
                    "mission-id-mismatch",
                    "Execution request mission ID does not match the persisted Mission.",
                )
            )

        known_tasks = frozenset(known_task_ids)
        missing_tasks = sorted(set(request.task_ids) - known_tasks)

        if missing_tasks:
            findings.append(
                self._error(
                    "unknown-task-ids",
                    "Execution request contains unknown task IDs: " + ", ".join(missing_tasks),
                )
            )

        for key, expected in sorted(required_source_fingerprints.items()):
            actual = request.source_fingerprints.get(key)

            if actual is None:
                findings.append(
                    self._error(
                        "missing-source-fingerprint",
                        f"Missing source fingerprint: {key}",
                    )
                )
                continue

            if actual != expected:
                findings.append(
                    self._error(
                        "source-fingerprint-mismatch",
                        f"Source fingerprint mismatch: {key}",
                    )
                )

        if not request.requested_operations:
            findings.append(
                self._error(
                    "missing-operations",
                    "Execution request must declare at least one operation.",
                )
            )

        if not request.task_ids:
            findings.append(
                self._error(
                    "missing-tasks",
                    "Execution request must select at least one task.",
                )
            )

        if not request.dry_run and not configuration.allow_dispatch:
            findings.append(
                self._error(
                    "dispatch-disabled",
                    "Non-dry-run execution is not permitted while tool dispatch is disabled.",
                )
            )

        return self._result(findings)

    def validate_approval_record(
        self,
        request: ExecutionRequest,
        approval: ApprovalRecord | None,
        configuration: ExecutionControllerConfiguration,
    ) -> ExecutionValidationResult:
        findings: list[ExecutionValidationFinding] = []

        try:
            validate_approval(
                request,
                approval,
                configuration,
            )
        except Exception as exc:
            findings.append(
                self._error(
                    "approval-invalid",
                    str(exc),
                )
            )
            return self._result(findings)

        if approval is None:
            return self._result(findings)

        if approval.decision is ApprovalDecision.APPROVED and not approval.approved_operations:
            findings.append(
                self._error(
                    "approval-scope-empty",
                    "Approved execution must declare approved operations.",
                )
            )

        undeclared = sorted(set(approval.approved_operations) - set(request.requested_operations))

        if undeclared:
            findings.append(
                self._error(
                    "approval-scope-mismatch",
                    "Approval contains undeclared operations: " + ", ".join(undeclared),
                )
            )

        return self._result(findings)

    def validate_operation(
        self,
        request: ExecutionRequest,
        approval: ApprovalRecord,
        operation: ExecutionOperation,
        registered_tools: frozenset[str],
    ) -> ExecutionValidationResult:
        findings: list[ExecutionValidationFinding] = []

        try:
            validate_registered_tool(
                operation,
                registered_tools,
            )
        except Exception as exc:
            findings.append(
                self._error(
                    "tool-not-registered",
                    str(exc),
                )
            )

        try:
            validate_operation_scope(
                request,
                approval,
                operation,
            )
        except Exception as exc:
            findings.append(
                self._error(
                    "operation-not-approved",
                    str(exc),
                )
            )

        if request.dry_run and operation.status not in {
            operation.status.PENDING,
            operation.status.APPROVED,
            operation.status.QUEUED,
        }:
            findings.append(
                self._error(
                    "dry-run-operation-status",
                    "Dry-run execution cannot contain a mutating operation result.",
                )
            )

        return self._result(findings)

    def validate_session(
        self,
        session: ExecutionSession,
        configuration: ExecutionControllerConfiguration,
    ) -> ExecutionValidationResult:
        findings: list[ExecutionValidationFinding] = []

        if not configuration.enabled:
            raise ExecutionConfigurationError("Execution Controller is disabled.")

        if (
            session.current_state
            in {
                ExecutionState.APPROVED,
                ExecutionState.QUEUED,
                ExecutionState.RUNNING,
                ExecutionState.BLOCKED,
                ExecutionState.CANCELLING,
                ExecutionState.COMPLETED,
            }
            and session.approval is None
        ):
            findings.append(
                self._error(
                    "session-approval-missing",
                    "Execution session state requires approval.",
                )
            )

        if session.current_state is ExecutionState.COMPLETED and any(
            operation.status.value
            in {
                "pending",
                "approved",
                "queued",
                "running",
                "failed",
                "blocked",
            }
            for operation in session.operations
        ):
            findings.append(
                self._error(
                    "completed-session-incomplete",
                    "Completed session contains unfinished or unsuccessful operations.",
                )
            )

        if is_terminal_state(session.current_state) and any(
            operation.status.value == "running" for operation in session.operations
        ):
            findings.append(
                self._error(
                    "terminal-session-running-operation",
                    "Terminal execution session contains a running operation.",
                )
            )

        transition_ids = [transition.transition_id for transition in session.transitions]

        if len(transition_ids) != len(set(transition_ids)):
            findings.append(
                self._error(
                    "duplicate-transition-ids",
                    "Execution transition IDs must be unique.",
                )
            )

        return self._result(findings)

    def validate_or_raise(
        self,
        result: ExecutionValidationResult,
    ) -> ExecutionValidationResult:
        if not result.valid:
            messages = "; ".join(finding.message for finding in result.findings if finding.is_error)

            raise ExecutionValidationError(messages or "Execution validation failed.")

        return result

    def _result(
        self,
        findings: list[ExecutionValidationFinding],
    ) -> ExecutionValidationResult:
        ordered = tuple(
            sorted(
                findings,
                key=lambda item: (
                    item.code,
                    item.message,
                    item.is_error,
                ),
            )
        )

        return ExecutionValidationResult(
            valid=not any(finding.is_error for finding in ordered),
            findings=ordered,
        )

    def _error(
        self,
        code: str,
        message: str,
    ) -> ExecutionValidationFinding:
        return ExecutionValidationFinding(
            code=code,
            message=message,
            is_error=True,
        )
