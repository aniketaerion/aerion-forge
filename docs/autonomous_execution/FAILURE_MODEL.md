# M5.2 Failure Model

## Failure Classes

- eligibility_failure
- dependency_failure
- authority_failure
- approval_failure
- lease_failure
- checkpoint_failure
- tool_resolution_failure
- argument_validation_failure
- tool_timeout
- tool_exit_failure
- scope_violation
- evidence_failure
- invariant_violation
- rollback_failure

## Recovery Mapping

- Retryable transient tool failures may retry within budget.
- Scope violations immediately stop execution and escalate.
- Authority and approval failures never auto-retry.
- Checkpoint failures block mutation.
- Rollback failure escalates.
- Exhausted budgets abort.