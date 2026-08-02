"""Validated application configuration loaded from environment variables."""

import os
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
    diagnostics_enabled: bool = True
    diagnostics_strict: bool = True
    diagnostics_history_limit: int = Field(default=5, ge=0, le=100)
    diagnostics_include_optional: bool = True
    diagnostics_write_probe_enabled: bool = True
    planning_enabled: bool = True
    planning_strict: bool = False
    planning_history_limit: int = Field(default=5, ge=0, le=100)
    planning_max_affected_areas: int = Field(default=25, ge=1, le=1000)
    planning_max_workstreams: int = Field(default=8, ge=1, le=50)
    planning_max_assumptions: int = Field(default=12, ge=1, le=100)
    planning_max_questions: int = Field(default=12, ge=1, le=100)
    planning_require_current_graph: bool = True
    planning_allow_degraded_runtime: bool = True

    task_management_enabled: bool = True
    task_management_strict: bool = False
    task_management_history_limit: int = Field(
        default=5,
        ge=0,
        le=100,
    )
    task_management_max_tasks_per_mission: int = Field(
        default=250,
        ge=1,
        le=5000,
    )
    task_management_max_dependencies_per_task: int = Field(
        default=25,
        ge=0,
        le=250,
    )
    task_management_max_acceptance_criteria_per_task: int = Field(
        default=25,
        ge=1,
        le=250,
    )
    task_management_max_validation_requirements_per_task: int = Field(
        default=25,
        ge=1,
        le=250,
    )
    task_management_require_approved_mission: bool = True
    task_management_allow_blocked_tasks: bool = True

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

    @classmethod
    def from_runtime(cls) -> "Settings":
        """Build the compatibility facade from the canonical runtime resolver."""
        from forge.configuration.resolver import ConfigurationResolver

        excluded = {"AERION_WORKSPACE_PATH", "AERION_REPORTS_PATH", "AERION_MEMORY_PATH"}
        environment = {key: value for key, value in os.environ.items() if key not in excluded}
        snapshot = ConfigurationResolver(Path.cwd()).resolve(environment=environment)
        values = {item.key: item.value for item in snapshot.settings}
        settings = cls(
            log_level=str(values["logging.level"]),
            ollama_model=str(values["core.ollama_model"]),
            ollama_base_url=str(values["core.ollama_base_url"]),
            command_timeout_seconds=int(values["core.command_timeout"]),
            index_max_hash_bytes=int(values["indexing.max_file_size"]),
            index_hash_chunk_bytes=int(values["indexing.chunk_size"]),
            index_max_files=int(values["indexing.max_files"]),
            graph_max_nodes=int(values["knowledge_graph.max_nodes"]),
            graph_max_edges=int(values["knowledge_graph.max_edges"]),
            graph_max_module_depth=int(values["knowledge_graph.max_module_depth"]),
            graph_include_directory_nodes=bool(values["knowledge_graph.include_directory_nodes"]),
            capability_registry_enabled=bool(values["capabilities.registry_enabled"]),
            capability_disabled_ids=",".join(values["capabilities.disabled_ids"]),
            capability_include_planned=bool(values["capabilities.include_planned"]),
            capability_strict_validation=bool(values["capabilities.strict_validation"]),
            capability_history_limit=int(values["capabilities.history_limit"]),
            diagnostics_enabled=bool(values["diagnostics.enabled"]),
            diagnostics_strict=bool(values["diagnostics.strict"]),
            diagnostics_history_limit=int(values["diagnostics.history_limit"]),
            diagnostics_include_optional=bool(values["diagnostics.include_optional"]),
            diagnostics_write_probe_enabled=bool(values["diagnostics.write_probe_enabled"]),
            planning_enabled=bool(values["planning.enabled"]),
            planning_strict=bool(values["planning.strict"]),
            planning_history_limit=int(values["planning.history_limit"]),
            planning_max_affected_areas=int(values["planning.max_affected_areas"]),
            planning_max_workstreams=int(values["planning.max_workstreams"]),
            planning_max_assumptions=int(values["planning.max_assumptions"]),
            planning_max_questions=int(values["planning.max_questions"]),
            planning_require_current_graph=bool(values["planning.require_current_graph"]),
            planning_allow_degraded_runtime=bool(values["planning.allow_degraded_runtime"]),
            task_management_enabled=bool(values["tasks.enabled"]),
            task_management_strict=bool(values["tasks.strict"]),
            task_management_history_limit=int(values["tasks.history_limit"]),
            task_management_max_tasks_per_mission=int(values["tasks.max_tasks_per_mission"]),
            task_management_max_dependencies_per_task=int(
                values["tasks.max_dependencies_per_task"]
            ),
            task_management_max_acceptance_criteria_per_task=int(
                values["tasks.max_acceptance_criteria_per_task"]
            ),
            task_management_max_validation_requirements_per_task=int(
                values["tasks.max_validation_requirements_per_task"]
            ),
            task_management_require_approved_mission=bool(values["tasks.require_approved_mission"]),
            task_management_allow_blocked_tasks=bool(values["tasks.allow_blocked_tasks"]),
            allow_shell=bool(values["security.allow_shell"]),
            allow_docker=bool(values["security.allow_docker"]),
            allow_database=bool(values["security.allow_database"]),
            _env_file=None,  # type: ignore[call-arg]
        )
        canonical_paths: dict[str, Path] = {}
        if "FORGE_WORKSPACE_STORE_PATH" in os.environ:
            canonical_paths["workspace_path"] = Path(str(values["workspace.store_path"])).parent
        if "FORGE_REPORTING_OUTPUT_DIRECTORY" in os.environ:
            canonical_paths["reports_path"] = Path(str(values["reporting.output_directory"]))
        if "FORGE_PERSISTENCE_MEMORY_DIRECTORY" in os.environ:
            canonical_paths["memory_path"] = Path(str(values["persistence.memory_directory"]))
        return settings.model_copy(update=canonical_paths)

    def ensure_runtime_directories(self) -> None:
        """Create directories owned by the agent, never the target repository."""
        for path in (self.workspace_path, self.reports_path, self.memory_path, self.logs_path):
            path.mkdir(parents=True, exist_ok=True)
