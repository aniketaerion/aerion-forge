# Autonomous Runtime Event Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Event envelope

`	ext
event_id
schema_version
mission_id
sequence
event_type
actor
previous_state
new_state
correlation_id
causation_id
payload
occurred_at
`

## Event families

Mission:

`	ext
MISSION_RECEIVED
MISSION_QUALIFIED
MISSION_CLARIFICATION_REQUESTED
MISSION_CONTEXT_READY
MISSION_PLAN_READY
MISSION_APPROVAL_REQUESTED
MISSION_APPROVED
MISSION_PAUSED
MISSION_RESUMED
MISSION_BLOCKED
MISSION_ESCALATED
MISSION_CANCELLED
MISSION_COMPLETED
MISSION_FAILED
`

Step and plan:

`	ext
PLAN_CREATED
PLAN_REVISED
PLAN_INVALIDATED
STEP_READY
STEP_STARTED
STEP_TOOL_INVOKED
STEP_TOOL_COMPLETED
STEP_VALIDATION_COMPLETED
STEP_REVIEWED
STEP_COMPLETED
STEP_FAILED
STEP_RETRY_SCHEDULED
STEP_ROLLED_BACK
`

Authority and recovery:

`	ext
AUTHORITY_EVALUATED
AUTHORITY_GRANTED
AUTHORITY_DENIED
APPROVAL_ISSUED
APPROVAL_REVOKED
APPROVAL_EXPIRED
CHECKPOINT_CREATED
CHECKPOINT_VERIFIED
ROLLBACK_STARTED
ROLLBACK_COMPLETED
ROLLBACK_FAILED
REPLAN_REQUESTED
INVARIANT_VIOLATION_DETECTED
FINAL_EVIDENCE_BUNDLE_CREATED
`

## Guarantees

- Sequence increases strictly per mission.
- Events are append-only.
- Consumers are idempotent.
- Snapshot update and event append form one logical transaction.
- Payloads are schema-versioned and redacted.
- Secrets, tokens, keys, passwords, and raw environment values are prohibited.