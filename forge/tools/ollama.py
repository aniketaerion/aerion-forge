"""Local Ollama HTTP API integration."""

import json
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from forge.tools.base import Tool, ToolResult


class OllamaTool(Tool):
    """Generate text and inspect models using a local Ollama daemon."""

    def __init__(self, base_url: str, model: str, timeout_seconds: int = 120) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout_seconds = timeout_seconds

    def validate(self, action: str, parameters: dict[str, Any]) -> None:
        if action not in {"health", "models", "generate"}:
            raise ValueError(f"Unsupported Ollama action: {action}")
        if action == "generate" and not str(parameters.get("prompt", "")).strip():
            raise ValueError("A non-empty prompt is required")

    def execute(self, action: str, parameters: dict[str, Any]) -> ToolResult:
        try:
            self.validate(action, parameters)
            if action == "generate":
                url = f"{self.base_url}/api/generate"
                body = json.dumps(
                    {
                        "model": parameters.get("model", self.model),
                        "prompt": parameters["prompt"],
                        "stream": False,
                    }
                ).encode()
                request = Request(
                    url, data=body, headers={"Content-Type": "application/json"}, method="POST"
                )
            else:
                url = (
                    f"{self.base_url}/api/tags"
                    if action == "models"
                    else f"{self.base_url}/api/version"
                )
                request = Request(url, method="GET")
            # The configured endpoint is expected to be the local Ollama daemon.
            with urlopen(request, timeout=self.timeout_seconds) as response:
                output = json.loads(response.read().decode("utf-8"))
            return ToolResult(success=True, output=output)
        except (HTTPError, URLError, TimeoutError, json.JSONDecodeError, ValueError) as exc:
            return ToolResult(success=False, error=str(exc))
