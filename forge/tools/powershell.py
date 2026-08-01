"""Permission-gated PowerShell process execution."""

import subprocess
from pathlib import Path
from typing import Any

from forge.tools.base import Tool, ToolResult


class PowerShellTool(Tool):
    """Run explicit PowerShell commands only when enabled by configuration."""

    def __init__(self, working_directory: Path, allowed: bool, timeout_seconds: int = 120) -> None:
        self.working_directory = working_directory.resolve()
        self.allowed = allowed
        self.timeout_seconds = timeout_seconds

    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        if action != "run":
            raise ValueError(f"Unsupported PowerShell action: {action}")
        if not self.allowed:
            raise PermissionError("PowerShell execution is disabled by tool permissions")
        command = parameters.get("command")
        if not isinstance(command, str) or not command.strip():
            raise ValueError("A non-empty command string is required")

    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        try:
            self.validate(action, parameters)
            completed = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", parameters["command"]],
                cwd=self.working_directory,
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
