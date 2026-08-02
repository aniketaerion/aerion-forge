# Execution Controller Acceptance Criteria

Milestone: 3.1

## Required evidence

- Architecture documents are complete and frozen.
- Models are strict, frozen, and deterministic.
- Execution requests preserve complete source lineage.
- Explicit approval is mandatory.
- Approval scope is enforced for every operation.
- Illegal transitions are rejected.
- Dry-run mode produces no target mutation.
- Store writes are atomic and rollback-safe.
- Reports are deterministic and complete.
- CLI commands return controlled exit codes.
- Capability registry truthfully reflects implementation.
- Existing milestones remain regression-clean.
- Ruff, Mypy, and pytest all pass.

## Release gate

M3.1 may be released only when:

1. Architecture is frozen.
2. Implementation validation scripts pass.
3. Acceptance evidence is recorded.
4. Capability registry is updated truthfully.
5. Documentation matches actual behaviour.
6. Full repository regression passes.
7. The milestone is committed, tagged, pushed, and merged into main.

## Architecture freeze rule

Changes to state names, approval semantics, trust boundaries, persistence paths,
public commands, or safety rules require an explicit architecture amendment.
