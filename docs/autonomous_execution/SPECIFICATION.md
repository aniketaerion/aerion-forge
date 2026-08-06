# M5.2 Autonomous Execution Engine Specification

## Functional Requirements

- Select the next eligible mission step deterministically.
- Reject steps with unmet dependencies.
- Reject actions exceeding granted authority.
- Reject high-risk actions without valid approval.
- Acquire a single-writer execution lease.
- Require a verified checkpoint before mutation.
- Resolve tools only from a registered allowlist.
- Validate tool arguments before invocation.
- Capture start time, end time, exit status, outputs, and affected files.
- Compare actual effects against approved scope.
- Emit ordered execution events.
- Persist execution evidence.
- Classify failures.
- Apply bounded retry, rollback, replan, pause, escalation, or abort decisions.
- Support simulation without mutation.
- Support inspection and reporting.

## Non-Functional Requirements

- Deterministic decisions
- Immutable evidence
- Typed errors
- Bounded execution
- Restart-safe state
- Secret redaction
- Auditability
- Testability
- No unrestricted shell
- No hidden repository mutation