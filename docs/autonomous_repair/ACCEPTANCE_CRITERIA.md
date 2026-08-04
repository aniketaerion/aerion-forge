# M3.5 Acceptance Criteria

M3.5 is complete when:

- provider registration is deterministic;
- exact-patch and isolated Ruff-fix providers are implemented;
- proposals become valid M3.3 requests;
- dry-run never changes the real repository;
- apply requires explicit approval;
- repository fingerprints are verified;
- changed files and bytes are bounded;
- post-repair validation uses M3.4;
- failed validation rolls back exact original bytes;
- repeated identical proposals are blocked;
- attempt limits are enforced;
- CLI, reports and validation scripts pass.