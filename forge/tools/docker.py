"""Docker CLI inspection with mutation permission boundaries."""

import subprocess
from pathlib import Path
from typing import Any, ClassVar

from forge.tools.base import Tool, ToolResult


class DockerTool(Tool):
    """Run bounded Docker inspection and optionally permission-gated lifecycle commands."""

    READ_ACTIONS: ClassVar[dict[str, list[str]]] = {
        "version": ["docker", "version"],
        "ps": ["docker", "ps"],
        "images": ["docker", "images"],
    }
    WRITE_ACTIONS: ClassVar[dict[str, list[str]]] = {
        "compose_up": ["docker", "compose", "up", "-d"],
        "compose_down": ["docker", "compose", "down"],
    }

    def __init__(
        self, working_directory: Path, allow_mutation: bool, timeout_seconds: int = 120
    ) -> None:
        self.working_directory = working_directory.resolve()
        self.allow_mutation = allow_mutation
        self.timeout_seconds = timeout_seconds

    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        if action not in self.READ_ACTIONS | self.WRITE_ACTIONS.keys():
            raise ValueError(f"Unsupported Docker action: {action}")
        if action in self.WRITE_ACTIONS and not self.allow_mutation:
            raise PermissionError("Docker mutation is disabled by tool permissions")

    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        try:
            self.validate(action, parameters)
            command = (self.READ_ACTIONS | self.WRITE_ACTIONS)[action]
            completed = subprocess.run(
                command,
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
