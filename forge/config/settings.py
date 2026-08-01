"""Validated application configuration loaded from environment variables."""

from pathlib import Path

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class ToolPermissions(BaseModel):
    """Explicit capability switches for tools that can mutate external state."""

    allow_shell: bool = False
    allow_docker: bool = False
    allow_database: bool = False


class Settings(BaseSettings):
    """Runtime settings with paths normalized relative to the invocation directory."""

    model_config = SettingsConfigDict(
        env_file=".env", env_prefix="AERION_", extra="ignore", case_sensitive=False
    )

    repository_path: Path = Field(default_factory=Path.cwd)
    workspace_path: Path = Path("workspaces")
    reports_path: Path = Path("reports/latest")
    memory_path: Path = Path("memory")
    logs_path: Path = Path("logs")
    prompts_path: Path | None = None
    log_level: str = "INFO"
    ollama_model: str = "qwen2.5-coder:7b"
    ollama_base_url: str = "http://localhost:11434"
    command_timeout_seconds: int = Field(default=120, ge=1, le=3600)
    index_max_hash_bytes: int = Field(default=10 * 1024 * 1024, ge=1024)
    index_hash_chunk_bytes: int = Field(default=64 * 1024, ge=1024, le=1024 * 1024)
    index_max_files: int = Field(default=250_000, ge=1)
    graph_max_nodes: int = Field(default=100_000, ge=1)
    graph_max_edges: int = Field(default=300_000, ge=1)
    graph_max_module_depth: int = Field(default=2, ge=1, le=10)
    graph_include_directory_nodes: bool = True
    capability_registry_enabled: bool = True
    capability_disabled_ids: str = ""
    capability_include_planned: bool = True
    capability_strict_validation: bool = True
    capability_history_limit: int = Field(default=5, ge=0, le=100)
    allow_shell: bool = False
    allow_docker: bool = False
    allow_database: bool = False

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, value: str) -> str:
        """Normalize and validate standard Python logging levels."""
        normalized = value.upper()
        if normalized not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError(f"Unsupported log level: {value}")
        return normalized

    @model_validator(mode="after")
    def normalize_paths(self) -> "Settings":
        """Resolve paths, then create only agent-owned output directories."""
        base = Path.cwd()
        for name in (
            "repository_path",
            "workspace_path",
            "reports_path",
            "memory_path",
            "logs_path",
        ):
            path = getattr(self, name).expanduser()
            setattr(
                self, name, (base / path).resolve() if not path.is_absolute() else path.resolve()
            )
        if self.prompts_path is None:
            self.prompts_path = Path(__file__).resolve().parents[1] / "prompts"
        else:
            prompt_path = self.prompts_path.expanduser()
            self.prompts_path = (
                (base / prompt_path).resolve()
                if not prompt_path.is_absolute()
                else prompt_path.resolve()
            )
        return self

    @property
    def permissions(self) -> ToolPermissions:
        """Return tool permissions as an immutable-by-convention value object."""
        return ToolPermissions(
            allow_shell=self.allow_shell,
            allow_docker=self.allow_docker,
            allow_database=self.allow_database,
        )

    @property
    def disabled_capability_ids(self) -> tuple[str, ...]:
        """Return normalized, deterministic capability disable declarations."""
        return tuple(
            sorted(
                {item.strip() for item in self.capability_disabled_ids.split(",") if item.strip()}
            )
        )

    def ensure_runtime_directories(self) -> None:
        """Create directories owned by the agent, never the target repository."""
        for path in (self.workspace_path, self.reports_path, self.memory_path, self.logs_path):
            path.mkdir(parents=True, exist_ok=True)
