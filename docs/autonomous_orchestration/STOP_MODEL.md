# M5.3 Orchestration Stop Model

## Mandatory Stop Conditions

- Approval required
- Authority insufficient
- Mission paused or cancelled
- Plan-version mismatch
- Session-version conflict
- Cycle budget exhausted
- Retry budget exhausted
- Rollback budget exhausted
- Replan budget exhausted
- Scope violation
- Invariant violation
- Checkpoint verification failure
- Rollback failure
- Terminal mission state
- Human escalation required

## Stop Categories

- awaiting_approval
- blocked
- paused
- escalated
- completed
- failed
- cancelled

Every stop includes a reason, resumability flag, and evidence references.