# M3.3 Acceptance Criteria

M3.3 is complete when:

- immutable contracts cover requests, operations, plans, snapshots and results;
- deterministic IDs and source fingerprints are implemented;
- only insert, replace and delete operations are supported;
- invalid paths and traversal are rejected;
- protected paths and symlink escapes are rejected;
- binary and oversized files are rejected;
- stale fingerprints and expected-text mismatches are rejected;
- overlapping edits are rejected;
- dry-run never writes;
- apply mode requires explicit approval;
- multi-file writes roll back on failure;
- unified diffs and structured reports are generated;
- Ruff, MyPy, the full pytest suite and M3.3 validation scripts pass.