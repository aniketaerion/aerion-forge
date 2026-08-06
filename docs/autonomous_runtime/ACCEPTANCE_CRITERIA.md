# M5.1 Autonomous Runtime Acceptance Criteria

**Status:** Architecture Draft  
**Version:** 0.2  
**Last Updated:** 2026-08-06

## Architecture

- [ ] Mission-driven architecture is implemented.
- [ ] Phase 1–4 integrations are explicit.
- [ ] Module boundaries are enforced.
- [ ] Multi-agent mutation is deferred.
- [ ] Snapshots and event journal have separate responsibilities.

## Data and state

- [ ] Core contracts are immutable and schema-versioned.
- [ ] Every state is defined once.
- [ ] Legal transitions have guards.
- [ ] Illegal transitions raise typed errors.
- [ ] Terminal states cannot resume.
- [ ] Completion requires objective, evidence, validation, scope compliance, and review.

## Authority and recovery

- [ ] A0–A6 and R0–R5 are machine-enforceable.
- [ ] Approval scope, expiry, revocation, and invalidation are enforced.
- [ ] A4–A6 require explicit approval.
- [ ] Mutation requires a verified checkpoint.
- [ ] Retry and replan budgets are finite.
- [ ] Rollback verifies the restored fingerprint.
- [ ] Rollback failure stops autonomous execution.

## Runtime and events

- [ ] Runtime executes one step at a time.
- [ ] Tool actions pass through one gateway.
- [ ] Review engine is read-only.
- [ ] Events are ordered, append-only, redacted, and idempotent.
- [ ] Mission state survives restart.

## CLI and validation

- [ ] CLI creates dry-run missions.
- [ ] CLI inspects missions.
- [ ] CLI simulates legal transitions and rejects illegal transitions.
- [ ] CLI generates reports.
- [ ] Ruff passes.
- [ ] MyPy passes.
- [ ] Focused M5.1 tests pass.
- [ ] Full repository tests pass.
- [ ] M5.1 architecture and completion validators pass.
- [ ] No unrestricted autonomous mutation exists in M5.1.