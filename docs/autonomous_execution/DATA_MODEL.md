# M5.2 Autonomous Execution Data Model

## Core Models

### ExecutionRequest

- request_id
- mission_id
- plan_id
- step_id
- repository_root
- dry_run
- requested_by
- created_at

### ExecutionLease

- lease_id
- mission_id
- repository_root
- holder
- acquired_at
- expires_at
- released_at
- version

### ToolDefinition

- tool_name
- action_kinds
- authority_required
- risk_class
- mutates_repository
- requires_checkpoint
- argument_schema
- timeout_seconds

### ToolExecutionRequest

- invocation_id
- mission_id
- step_id
- tool_name
- action_kind
- arguments
- approved_scope
- checkpoint_id
- approval_id
- dry_run

### ToolExecutionResult

- invocation_id
- status
- exit_code
- stdout_reference
- stderr_reference
- affected_files
- result_digest
- started_at
- completed_at

### StepExecutionRecord

- execution_id
- mission_id
- step_id
- attempt_number
- lease_id
- checkpoint_id
- invocation_ids
- evidence_ids
- status
- failure_class
- started_at
- completed_at

## Invariants

- One active lease per repository.
- One active step execution per mission.
- Mutating tools require verified checkpoints.
- Actual affected files must remain inside approved scope.
- Tool execution records are immutable.
- Completed executions require evidence.