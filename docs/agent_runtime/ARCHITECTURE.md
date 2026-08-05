# M3.8 Unified Agent Runtime Architecture

M3.8 connects existing Forge engineering capabilities into one controlled,
persistent, end-to-end agent runtime.

The runtime does not replace the existing modules. It coordinates them through
typed adapters, explicit stages, approval boundaries, checkpoints, telemetry,
and release evidence.

## Runtime layers

1. Contracts and policy
2. Capability adapters
3. Capability registry
4. Stage graph and lifecycle state machine
5. Session executor
6. Persistence and checkpoints
7. Recovery and telemetry
8. Reporting and CLI
9. Build-verification release gate

## Design principle

Every stage must be independently testable, auditable, resumable, and bounded.
No capability may bypass the approval or release gates.