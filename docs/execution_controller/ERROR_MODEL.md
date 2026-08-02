# Execution Controller Error Model

Milestone: 3.1

## Error categories

- ExecutionControllerError
- ExecutionConfigurationError
- ExecutionValidationError
- ExecutionRequestNotFoundError
- ExecutionSessionNotFoundError
- ExecutionApprovalRequiredError
- ExecutionApprovalRejectedError
- ExecutionApprovalMismatchError
- ExecutionStateTransitionError
- ExecutionToolNotRegisteredError
- ExecutionOperationNotApprovedError
- ExecutionDispatchError
- ExecutionPersistenceError
- ExecutionReportError
- ExecutionCancellationError

## Failure behaviour

- Validation failure dispatches no operation.
- Missing approval leaves the request awaiting approval.
- Approval mismatch rejects execution.
- Illegal transitions do not modify persisted state.
- Tool failure records operation and evidence details.
- Persistence failure restores the previous valid store and reports.
- Cancellation is not complete until active work is safely stopped.
- Failures must never be silently converted into success.
- Target mutation must never be retried without explicit policy.
