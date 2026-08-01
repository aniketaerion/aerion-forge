"""Read-only, repository-confined filesystem operations."""

import hashlib
from pathlib import Path
from typing import Any

from forge.tools.base import Tool, ToolResult


class FilesystemTool(Tool):
    """Inspect files beneath an allowed root without mutating target content."""

    def __init__(self, root: Path, max_read_bytes: int = 2_000_000) -> None:
        self.root = root.resolve()
        self.max_read_bytes = max_read_bytes

    def _resolve(self, raw_path: str) -> Path:
        path = (self.root / raw_path).resolve()
        if path != self.root and self.root not in path.parents:
            raise PermissionError(f"Path escapes repository root: {raw_path}")
        return path

    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        if action not in {"read_text", "list", "stat", "hash"}:
            raise ValueError(f"Unsupported filesystem action: {action}")
        path = self._resolve(str(parameters.get("path", ".")))
        if not path.exists():
            raise FileNotFoundError(path)
        if action == "read_text" and (
            not path.is_file() or path.stat().st_size > self.max_read_bytes
        ):
            raise ValueError(f"File is not readable or exceeds {self.max_read_bytes} bytes: {path}")

    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        try:
            self.validate(action, parameters)
            path = self._resolve(str(parameters.get("path", ".")))
            if action == "read_text":
                output: Any = path.read_text(encoding=str(parameters.get("encoding", "utf-8")))
            elif action == "list":
                recursive = bool(parameters.get("recursive", False))
                iterator = path.rglob("*") if recursive else path.iterdir()
                output = sorted(item.relative_to(self.root).as_posix() for item in iterator)
            elif action == "stat":
                stat = path.stat()
                output = {
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "is_file": path.is_file(),
                }
            else:
                output = hashlib.sha256(path.read_bytes()).hexdigest()
            return ToolResult(success=True, output=output)
        except (OSError, UnicodeError, ValueError, PermissionError) as exc:
            return ToolResult(success=False, error=str(exc))
