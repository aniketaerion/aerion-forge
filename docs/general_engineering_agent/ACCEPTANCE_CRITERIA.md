# M5.9 General Engineering Agent Acceptance Criteria

M5.9 is complete only when:

1. previously unseen natural-language software tasks are accepted;
2. repository inspection occurs before change planning;
3. relevant files and symbols are selected using evidence;
4. every planned target has traceable rationale;
5. plans are structured rather than prose-only;
6. PLAN approval is enforced according to policy;
7. provider-specific reasoning is isolated behind EngineeringProvider contracts;
8. edit proposals are structured and validated;
9. provider output cannot mutate repository files directly;
10. EDIT approval is enforced according to policy;
11. safe single-file edits are supported;
12. bounded multi-file edits are supported;
13. forbidden paths and scope boundaries are enforced;
14. source fingerprints prevent stale destructive edits where required;
15. repository-specific validation runs after mutation;
16. validation failures produce evidence;
17. bounded repair proposals can be generated;
18. repair-attempt limits are enforced;
19. repeated failure terminates safely;
20. RELEASE approval is enforced according to policy;
21. end-to-end evidence links request, plan, approvals, edits, validation, repair, and result;
22. deterministic fake-provider tests pass;
23. no acceptance-task-specific implementation is encoded in Forge;
24. an unfamiliar single-file acceptance mission passes;
25. an unfamiliar multi-file acceptance mission passes;
26. an ERP-style or business-rule acceptance mission passes;
27. architecture validation passes;
28. Ruff passes;
29. MyPy passes;
30. focused and integration tests pass;
31. the full Forge regression suite passes;
32. worktree and release-gate requirements are clean before tagging.

## Prohibited Acceptance Shortcut
M5.9 must not be declared complete solely by demonstrating predefined calculator operations or another task explicitly encoded into Forge implementation logic.