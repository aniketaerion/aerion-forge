"""PostgreSQL CLI tool with read-only SQL enforcement by default."""

import re
import subprocess
from typing import Any

from forge.tools.base import Tool, ToolResult


class PostgreSQLTool(Tool):
    """Execute SQL through psql with conservative statement validation."""

    READ_ONLY = re.compile(r"^\s*(SELECT|SHOW|EXPLAIN|WITH)\b", re.IGNORECASE)

    def __init__(
        self, connection_uri: str | None, allow_mutation: bool, timeout_seconds: int = 120
    ) -> None:
        self.connection_uri = connection_uri
        self.allow_mutation = allow_mutation
        self.timeout_seconds = timeout_seconds

    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        if action != "query":
            raise ValueError(f"Unsupported PostgreSQL action: {action}")
        if not self.connection_uri:
            raise ValueError("PostgreSQL connection URI is not configured")
        query = parameters.get("query")
        if not isinstance(query, str) or not query.strip():
            raise ValueError("A non-empty SQL query is required")
        if not self.allow_mutation and not self.READ_ONLY.match(query):
            raise PermissionError("Only read-only SQL is permitted")

    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        try:
            self.validate(action, parameters)
            completed = subprocess.run(
                ["psql", self.connection_uri or "", "-X", "--no-psqlrc", "-c", parameters["query"]],
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return ToolResult(
                success=completed.returncode == 0,
                output=completed.stdout,
                error=completed.stderr or None,
                metadata={"return_code": completed.returncode},
            )
        except (OSError, subprocess.SubprocessError, ValueError, PermissionError) as exc:
            return ToolResult(success=False, error=str(exc))
