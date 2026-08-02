# Safe Change Planning Acceptance Criteria

## Required evidence

- All eight architecture documents are populated.
- Architecture headings pass the validation guard.
- Models are frozen, typed, canonical, and deterministic.
- IDs and fingerprints are repeatable.
- Change targets and dependency impacts are traceable.
- Risk classification is deterministic.
- Verification planning covers every mutating action.
- Rollback limitations are explicit.
- Invalid lineage fails safely.
- Planner performs no execution.
- Renderer produces all declared artifacts.
- Writes are atomic and recoverable.
- CLI is registered and tested.
- Capability catalogue truth is updated.
- Ruff passes.
- MyPy passes.
- Full Pytest suite passes.
- Working tree is clean before release tagging.

## Release gate

M3.2 may be released only when:

1. Architecture package passes.
2. Package A passes.
3. Package B passes.
4. Completion package passes.
5. Full repository regression passes.
6. Capability registry reports `safe-change-planning` as available and implemented.
7. Final commit is tagged.
8. The milestone is merged into `main`.
9. `main` passes the same validation suite.

## Prohibited release conditions

Release is blocked if:

- any required document is empty,
- any test fails,
- any type or lint error exists,
- the planner mutates the target repository,
- the planner dispatches tools,
- risk controls can be bypassed,
- capability catalogue truth is inconsistent,
- Git working tree contains unexplained changes.
