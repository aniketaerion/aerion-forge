# M4.2 Backend Security Model

Backend analysis is fail-closed.

- Network access is disabled.
- Process execution is disabled.
- Source modification is disabled.
- Secret inspection is disabled.
- Repository path escape is rejected.
- File inspection is bounded.
- No application module is imported or executed during analysis.