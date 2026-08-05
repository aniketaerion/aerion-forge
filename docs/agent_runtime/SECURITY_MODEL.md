# M3.8 Unified Agent Runtime Security Model

The runtime is fail-closed.

- Code changes are disabled by default.
- Network access is disabled by default.
- Self-modification is disabled by default.
- Plan, edit, repair, and release approvals are explicit.
- Capabilities are allow-listed.
- Stage counts and repair attempts are bounded.
- Repository-relative path escape is rejected.
- All stage outputs must be captured as evidence.
- The runtime never merges, tags, publishes, or deploys automatically.