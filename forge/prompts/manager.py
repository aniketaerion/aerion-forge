"""Safe file-backed prompt template management."""

from pathlib import Path
from string import Template


class PromptManager:
    """Load named prompt files and substitute explicitly supplied variables."""

    def __init__(self, prompts_path: Path) -> None:
        self.prompts_path = prompts_path.resolve()

    def load(self, name: str) -> str:
        """Load a UTF-8 prompt while preventing directory traversal."""
        candidate = (self.prompts_path / name).resolve()
        if self.prompts_path not in candidate.parents:
            raise ValueError("Prompt path escapes the configured prompt directory")
        if not candidate.is_file():
            raise FileNotFoundError(f"Prompt not found: {name}")
        return candidate.read_text(encoding="utf-8")

    def render(self, name: str, variables: dict[str, object]) -> str:
        """Render a prompt using strict ``${variable}`` substitution."""
        string_values = {key: str(value) for key, value in variables.items()}
        try:
            return Template(self.load(name)).substitute(string_values)
        except KeyError as exc:
            raise ValueError(f"Missing prompt variable: {exc.args[0]}") from exc
