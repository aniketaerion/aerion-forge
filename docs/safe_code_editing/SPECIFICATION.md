# M3.3 Safe Code Editing Specification

## Supported operations

- `insert`: add text at one verified offset.
- `replace`: replace verified expected text within one range.
- `delete`: remove verified expected text within one range.

## Required guarantees

- Every path remains inside the repository.
- Protected and generated paths are rejected.
- Dry-run is the default.
- Apply mode requires explicit approval.
- Source fingerprints detect stale plans.
- Overlapping edits are rejected.
- Unified diffs are generated before writes.
- Multi-file writes are atomic from the user perspective.
- Failures trigger rollback.

## Explicit exclusions

AST refactoring, symbol graph rewrites, dependency installation, autonomous commits and unrestricted commands are outside M3.3 v1.