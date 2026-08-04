# M3.4 Acceptance Criteria

M3.4 is complete when:

- Ruff, MyPy and Pytest commands are represented by immutable contracts;
- unsupported tools and shell metacharacters are rejected;
- timeouts are enforced;
- outputs are normalized into structured findings;
- repair candidates are bounded to explicit paths and findings;
- apply mode requires explicit approval;
- repair attempts cannot exceed policy limits;
- repository state changes stop execution;
- failed repair attempts roll back;
- final reports contain complete evidence;
- full project quality gates and M3.4 validation scripts pass.