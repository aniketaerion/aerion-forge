# Execution Controller Test Plan

Milestone: 3.1

## Test layers

- Model validation tests
- Identifier and fingerprint tests
- Approval-policy tests
- State-transition tests
- Validator tests
- Store and rollback tests
- Renderer tests
- Service orchestration tests
- CLI contract tests
- Capability-registry tests
- Full repository regression tests

## Safety tests

1. No execution without explicit approval.
2. No operation outside approved scope.
3. No illegal transition.
4. No mutation during dry-run.
5. No dispatch through an unregistered tool.
6. No partial persistence after write failure.
7. No silent retry after mutation failure.
8. No execution using stale approval.
9. No mutation of planning or reporting artifacts.
10. Terminal sessions reject further transitions.

## Quality gates

- Ruff passes
- Mypy passes
- Package tests pass
- Full pytest suite passes
- Validation scripts pass
- Git diff check passes
