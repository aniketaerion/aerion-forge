"""Read-only Git repository inspection backed by GitPython."""

from pathlib import Path
from typing import Any, ClassVar

from git import InvalidGitRepositoryError, NoSuchPathError, Repo

from forge.tools.base import Tool, ToolResult


class GitTool(Tool):
    """Expose Git metadata without staging, committing, or changing files."""

    ACTIONS: ClassVar[set[str]] = {"status", "branches", "log", "diff", "remotes"}

    def __init__(self, repository_path: Path) -> None:
        self.repository_path = repository_path.resolve()

    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        if action not in self.ACTIONS:
            raise ValueError(f"Unsupported read-only Git action: {action}")
        try:
            Repo(self.repository_path)
        except (InvalidGitRepositoryError, NoSuchPathError) as exc:
            raise ValueError(f"Not a Git repository: {self.repository_path}") from exc

    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        try:
            self.validate(action, parameters)
            repo = Repo(self.repository_path)
            if action == "status":
                output: Any = {
                    "dirty": repo.is_dirty(untracked_files=True),
                    "untracked": repo.untracked_files,
                }
            elif action == "branches":
                output = [head.name for head in repo.heads]
            elif action == "log":
                limit = min(max(int(parameters.get("limit", 20)), 1), 200)
                output = [
                    {"sha": commit.hexsha, "summary": commit.summary, "author": str(commit.author)}
                    for commit in repo.iter_commits(max_count=limit)
                ]
            elif action == "diff":
                output = repo.git.diff("--", str(parameters.get("path", ".")))
            else:
                output = [
                    {"name": remote.name, "urls": list(remote.urls)} for remote in repo.remotes
                ]
            return ToolResult(success=True, output=output)
        except (ValueError, RuntimeError, OSError) as exc:
            return ToolResult(success=False, error=str(exc))
