# Autonomous Runtime Recovery Model

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Checkpoint kinds

`	ext
GIT_COMMIT
GIT_STASH
WORKTREE_SNAPSHOT
FILE_SNAPSHOT
REVERSIBLE_PATCH
`

Every modifying step requires a verified checkpoint before execution.

## Failure classes

`	ext
TRANSIENT_TOOL_FAILURE
DETERMINISTIC_TOOL_FAILURE
VALIDATION_FAILURE
SCOPE_VIOLATION
AUTHORITY_FAILURE
APPROVAL_FAILURE
ENVIRONMENT_FAILURE
CHECKPOINT_FAILURE
ROLLBACK_FAILURE
INVARIANT_VIOLATION
BUDGET_EXHAUSTION
`

## Recovery actions

`	ext
RETRY_STEP
REPLAN
ROLLBACK_STEP
ROLLBACK_MISSION
PAUSE
ESCALATE
ABORT
`

## Default budgets

`	ext
maximum attempts per step: 2
maximum replans per mission: 2
maximum rollback attempts: 1
maximum consecutive tool failures: 3
maximum total execution cycles: 20
`

## Retry guard

Retry requires a retryable failure, unchanged valid authority, verified restored fingerprint, remaining budget, and no amplification of destructive effects.

## Rollback procedure

1. stop scheduling;
2. record process state;
3. select checkpoint;
4. verify metadata;
5. restore;
6. verify repository fingerprint;
7. run restoration checks;
8. append event;
9. retry, replan, pause, escalate, or fail.

Rollback failure stops autonomous mutation and transitions to FAILED or ESCALATED with manual recovery evidence.

Non-reversible actions require R4/R5 approval, compensating action, operator acknowledgement, and no automatic retry.