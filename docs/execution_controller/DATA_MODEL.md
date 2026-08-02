# Execution Controller Data Model

Milestone: 3.1
Schema version: 1.0

## Entities

### ExecutionRequest

- request_id
- request_fingerprint
- mission_id
- task_ids
- requested_operations
- dry_run
- source_fingerprints

### ApprovalRecord

- approval_id
- request_fingerprint
- approver_id
- decision
- approved_operations
- evidence_reference

### ExecutionSession

- session_id
- session_fingerprint
- request
- approval
- current_state
- transitions
- operations
- evidence
- statistics
- source_fingerprints

### ExecutionTransition

- transition_id
- previous_state
- event
- next_state
- reason
- evidence_ids

### ExecutionOperation

- operation_id
- task_id
- tool_id
- operation_type
- status
- result_reference
- failure_reference

### ExecutionStore

- active sessions
- bounded history
- schema version

## Invariants

- Identity fields cannot be blank.
- Mission lineage must match all source artifacts.
- Approval must match the active request fingerprint.
- Dispatched operations must be explicitly approved.
- Current state must equal the latest transition state.
- Terminal sessions cannot contain active operations.
- Dry-run sessions cannot contain target-mutating results.
- Evidence identifiers must be unique.
- Source fingerprints must be immutable and canonically ordered.
- Unknown fields must be rejected.
