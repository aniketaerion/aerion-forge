"""Repository audit planning."""


class AuditPlanner:
    """Produce a stable, inspectable plan for a read-only repository audit."""

    def build(self) -> list[str]:
        """Return ordered audit stages."""
        return [
            "Validate repository access and enumerate files",
            "Classify technology, architecture, configuration, and delivery assets",
            "Extract package manifests and build the dependency graph",
            "Inspect text sources for TODOs, FIXMEs, incomplete code, APIs, and routes",
            "Identify testing gaps and prioritize findings",
            "Persist audit memory and generate architecture reports",
        ]
