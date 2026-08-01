"""Abstract dependency-injected agent orchestration contract."""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from forge.config import Settings
from forge.memory import JsonMemoryStore
from forge.tools import Tool


class BaseAgent(ABC):
    """Provide planning, execution, memory, tools, logging, and reporting primitives."""

    def __init__(
        self,
        settings: Settings,
        logger: logging.Logger,
        memory: JsonMemoryStore,
        tools: dict[str, Tool],
    ) -> None:
        self.settings = settings
        self.logger = logger
        self.memory = memory
        self.tools = dict(tools)

    @abstractmethod
    def plan(self, **kwargs: Any) -> list[str]:
        """Return the concrete steps the agent will execute."""

    @abstractmethod
    def execute(self, **kwargs: Any) -> Any:
        """Execute the agent's bounded responsibility."""

    def write_report(self, filename: str, content: str) -> Path:
        """Write one report atomically inside the configured reports directory."""
        destination = (self.settings.reports_path / filename).resolve()
        if self.settings.reports_path.resolve() not in destination.parents:
            raise ValueError("Report path escapes the configured reports directory")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(f"{destination.suffix}.tmp")
        temporary.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
        temporary.replace(destination)
        return destination
