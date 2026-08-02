# Execution Controller State Machine

Milestone: 3.1

## States

- requested
- validating
- validation_failed
- awaiting_approval
- approval_rejected
- approved
- queued
- running
- blocked
- cancelling
- cancelled
- failed
- completed

## Transitions

| From | Event | To |
|---|---|---|
| requested | validate | validating |
| validating | validation_passed | awaiting_approval |
| validating | validation_failed | validation_failed |
| awaiting_approval | approve | approved |
| awaiting_approval | reject | approval_rejected |
| approved | enqueue | queued |
| queued | start | running |
| running | blocking_condition | blocked |
| running | fail | failed |
| running | complete | completed |
| running | cancel_requested | cancelling |
| cancelling | cancellation_complete | cancelled |

## Rules

- Every transition has a deterministic identity.
- Running requires valid approval.
- Terminal states cannot transition further.
- Failed and blocked states require a reason.
- Illegal transitions must not change persisted state.
- Re-execution requires a new session.
