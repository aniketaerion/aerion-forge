# Autonomous Runtime State Machine

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Primary flow

`	ext
RECEIVED -> QUALIFYING -> QUALIFIED -> CONTEXT_BUILDING -> CONTEXT_READY
-> PLANNING -> PLAN_READY -> AWAITING_APPROVAL -> APPROVED
-> EXECUTING -> VALIDATING -> REVIEWING -> COMPLETED
`

## Legal transitions

| From | To | Guard |
|---|---|---|
| RECEIVED | QUALIFYING | Request valid |
| QUALIFYING | QUALIFIED | Accepted |
| QUALIFYING | CLARIFICATION_REQUIRED | Required information missing |
| QUALIFYING | FAILED | Rejected |
| QUALIFYING | ESCALATED | Human decision required |
| CLARIFICATION_REQUIRED | QUALIFYING | Clarification supplied |
| QUALIFIED | CONTEXT_BUILDING | Capabilities available |
| CONTEXT_BUILDING | CONTEXT_READY | Context complete |
| CONTEXT_BUILDING | BLOCKED | Context dependency unavailable |
| CONTEXT_READY | PLANNING | Fingerprint valid |
| PLANNING | PLAN_READY | Plan structurally valid |
| PLANNING | BLOCKED | No safe plan |
| PLAN_READY | AWAITING_APPROVAL | Approval required |
| PLAN_READY | APPROVED | Automatic policy permits |
| AWAITING_APPROVAL | APPROVED | Valid approval issued |
| AWAITING_APPROVAL | CANCELLED | Denied and cancelled |
| APPROVED | EXECUTING | Preconditions, authority, checkpoint valid |
| EXECUTING | VALIDATING | Step execution ends |
| EXECUTING | ROLLING_BACK | Failure after mutation |
| EXECUTING | PAUSED | Authorized pause |
| EXECUTING | BLOCKED | Environment unavailable |
| VALIDATING | EXECUTING | Step passed; steps remain |
| VALIDATING | REVIEWING | Plan and validations complete |
| VALIDATING | ROLLING_BACK | Validation requires restoration |
| VALIDATING | PLANNING | Replan approved |
| REVIEWING | COMPLETED | Completion guard passes |
| REVIEWING | PLANNING | Revision and budget available |
| REVIEWING | ESCALATED | Human judgment required |
| ROLLING_BACK | ROLLED_BACK | Restoration verified |
| ROLLING_BACK | FAILED | Restoration failed |
| ROLLED_BACK | EXECUTING | Retry approved |
| ROLLED_BACK | PLANNING | Replan selected |
| PAUSED | EXECUTING | Resume checks pass |
| BLOCKED | CONTEXT_BUILDING | Context restored |
| BLOCKED | EXECUTING | Execution dependency restored |
| ESCALATED | AWAITING_APPROVAL | Escalation resolved |
| Any non-terminal | CANCELLED | Authorized cancellation |
| Any active | FAILED | Fatal invariant or unrecoverable error |

## Forbidden examples

- RECEIVED -> EXECUTING
- QUALIFIED -> COMPLETED
- PLAN_READY -> EXECUTING without approval evaluation
- VALIDATING -> COMPLETED without review
- FAILED, CANCELLED, or COMPLETED -> active state

## Transition guard order

1. current state;
2. legal transition;
3. non-terminal mission;
4. current version and lease;
5. available budgets;
6. authority;
7. approval;
8. evidence;
9. checkpoint;
10. transition-specific invariant.

## Completion guard

Completion requires objective satisfaction, required step completion, required validation, scope compliance, no critical finding, review approval, and persisted final evidence.