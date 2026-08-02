"""Read-only extraction of persisted Phase 1 planning evidence."""

import hashlib
import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from forge.discovery.models import DiscoveryResult
from forge.indexing.models import ProjectIndex
from forge.knowledge.models import KnowledgeGraph
from forge.planning.errors import (
    MissionContextError,
    MissionTargetNotFoundError,
)

_REQUIRED_CAPABILITIES = frozenset(
    {
        "workspace-management",
        "repository-discovery",
        "incremental-project-index",
        "engineering-knowledge-graph",
        "capability-registry",
        "runtime-configuration",
        "runtime-health-diagnostics",
        "phase-validation-release",
    }
)


class PlanningContext(BaseModel):
    """Safe, typed subset of existing persisted runtime state."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
    )

    target_identity: str
    target_name: str
    workspace_identity: str

    discovery: DiscoveryResult | None = None
    project_index: ProjectIndex | None = None
    graph: KnowledgeGraph | None = None

    graph_is_current: bool = False
    graph_staleness_reason: str | None = None

    diagnostic_status: str = "unknown"
    diagnostic_fingerprint: str = "missing"
    diagnostic_target_matches: bool = False

    capability_fingerprint: str = "missing"
    configuration_fingerprint: str = "missing"

    unavailable_capabilities: tuple[str, ...] = ()


def _read(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}

    try:
        value = json.loads(
            path.read_text(encoding="utf-8-sig")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise MissionContextError(
            "Persisted Phase 1 state is unreadable: "
            f"{path.name}"
        ) from exc

    if not isinstance(value, dict):
        raise MissionContextError(
            "Persisted Phase 1 state is invalid: "
            f"{path.name}"
        )

    return value


def _mapping(
    value: Any,
) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _identity(root: Path) -> str:
    portable_root = (
        root.resolve()
        .as_posix()
        .casefold()
    )

    return hashlib.sha256(
        portable_root.encode("utf-8")
    ).hexdigest()


def _resolve_target(
    workspaces: dict[str, Any],
    target: str | None,
    cwd: Path,
) -> tuple[Path, str, str]:
    records = _mapping(
        workspaces.get("workspaces")
    )

    selected: dict[str, Any] | None = None
    selected_id: str | None = None

    if target:
        for workspace_id, raw_record in sorted(
            records.items()
        ):
            record = _mapping(raw_record)
            name = str(
                record.get("name", "")
            )

            if (
                workspace_id == target
                or name.casefold()
                == target.casefold()
            ):
                selected = record
                selected_id = workspace_id
                break

        if selected is not None:
            repository_path = selected.get(
                "repository_path"
            )

            if not repository_path:
                raise MissionContextError(
                    "Workspace has no repository path."
                )

            root = Path(
                str(repository_path)
            ).expanduser()
        else:
            root = Path(target).expanduser()

            if not root.exists():
                raise MissionTargetNotFoundError(
                    "Workspace or repository path "
                    f"not found: {target}"
                )

    else:
        active_workspace_id = workspaces.get(
            "active_workspace_id"
        )

        if (
            isinstance(active_workspace_id, str)
            and active_workspace_id in records
        ):
            selected_id = active_workspace_id
            selected = _mapping(
                records[active_workspace_id]
            )

            repository_path = selected.get(
                "repository_path"
            )

            if not repository_path:
                raise MissionContextError(
                    "Active workspace has no "
                    "repository path."
                )

            root = Path(
                str(repository_path)
            ).expanduser()
        else:
            root = cwd

    if not root.exists():
        raise MissionTargetNotFoundError(
            "Resolved repository path does not exist."
        )

    root = root.resolve()

    target_identity = _identity(root)
    workspace_identity = (
        selected_id
        or target_identity
    )
    target_name = (
        str(selected.get("name"))
        if selected is not None
        else root.name
    )

    return (
        root,
        workspace_identity,
        target_name,
    )


def _load_discovery(
    memory_path: Path,
    workspace_identity: str,
    target_identity: str,
) -> DiscoveryResult | None:
    data = _read(
        memory_path / "discovery.json"
    )
    results = _mapping(
        data.get("results")
    )

    raw = (
        results.get(workspace_identity)
        or results.get(target_identity)
    )

    if raw is None:
        return None

    try:
        return DiscoveryResult.model_validate(raw)
    except ValidationError as exc:
        raise MissionContextError(
            "Persisted discovery state is invalid."
        ) from exc


def _load_index(
    memory_path: Path,
    workspace_identity: str,
    target_identity: str,
) -> ProjectIndex | None:
    data = _read(
        memory_path / "index.json"
    )
    repositories = _mapping(
        data.get("repositories")
    )

    raw = (
        repositories.get(target_identity)
        or repositories.get(workspace_identity)
    )

    if raw is None:
        return None

    try:
        return ProjectIndex.model_validate(raw)
    except ValidationError as exc:
        raise MissionContextError(
            "Persisted index state is invalid."
        ) from exc


def _load_graph(
    memory_path: Path,
    workspace_identity: str,
    target_identity: str,
) -> KnowledgeGraph | None:
    data = _read(
        memory_path / "knowledge_graph.json"
    )
    repositories = _mapping(
        data.get("repositories")
    )

    raw = (
        repositories.get(target_identity)
        or repositories.get(workspace_identity)
    )

    if raw is None:
        return None

    try:
        return KnowledgeGraph.model_validate(raw)
    except ValidationError as exc:
        raise MissionContextError(
            "Persisted knowledge graph is invalid."
        ) from exc


def _graph_freshness(
    project_index: ProjectIndex | None,
    graph: KnowledgeGraph | None,
) -> tuple[bool, str | None]:
    if graph is None:
        return (
            False,
            "Knowledge graph is missing.",
        )

    if project_index is None:
        return (
            False,
            "Project index is missing, so graph "
            "freshness cannot be verified.",
        )

    graph_generation = graph.generation
    index_generation = project_index.generation

    if (
        graph_generation.source_index_generation_id
        != index_generation.generation_id
    ):
        return (
            False,
            "Knowledge graph was built from a "
            "different index generation.",
        )

    if (
        graph_generation.source_index_state_fingerprint
        != index_generation.repository_state_fingerprint
    ):
        return (
            False,
            "Knowledge graph index fingerprint "
            "does not match the current index.",
        )

    return True, None


def _diagnostics(
    memory_path: Path,
    workspace_identity: str,
    target_identity: str,
) -> tuple[str, str, bool]:
    data = _read(
        memory_path / "diagnostics.json"
    )
    snapshots = _mapping(
        data.get("snapshots")
    )

    target_keys = (
        f"target:{workspace_identity}",
        f"target:{target_identity}",
    )

    snapshot: dict[str, Any] = {}

    for key in target_keys:
        candidate = snapshots.get(key)

        if isinstance(candidate, dict):
            snapshot = candidate
            break

    if not snapshot:
        runtime = snapshots.get("runtime")

        if isinstance(runtime, dict):
            summary = _mapping(
                runtime.get("summary")
            )

            return (
                str(
                    summary.get(
                        "overall_status",
                        "unknown",
                    )
                ),
                str(
                    runtime.get(
                        "diagnostic_fingerprint",
                        "missing",
                    )
                ),
                False,
            )

        return "missing", "missing", False

    summary = _mapping(
        snapshot.get("summary")
    )

    snapshot_target = snapshot.get(
        "target_identity"
    )

    target_matches = (
        snapshot_target in {
            None,
            workspace_identity,
            target_identity,
        }
    )

    return (
        str(
            summary.get(
                "overall_status",
                "unknown",
            )
        ),
        str(
            snapshot.get(
                "diagnostic_fingerprint",
                "missing",
            )
        ),
        target_matches,
    )


def _capabilities(
    memory_path: Path,
) -> tuple[str, tuple[str, ...]]:
    data = _read(
        memory_path / "capabilities.json"
    )

    current = _mapping(
        data.get("current", data)
    )
    generation = _mapping(
        current.get("generation")
    )

    fingerprint = str(
        generation.get(
            "registry_fingerprint",
            "missing",
        )
    )

    evaluations = current.get(
        "evaluations",
        ()
    )

    available: set[str] = set()

    if isinstance(evaluations, list | tuple):
        for raw_evaluation in evaluations:
            evaluation = _mapping(
                raw_evaluation
            )

            if evaluation.get("available") is True:
                capability_id = evaluation.get(
                    "capability_id"
                )

                if capability_id:
                    available.add(
                        str(capability_id)
                    )

    unavailable = tuple(
        sorted(
            _REQUIRED_CAPABILITIES
            - available
        )
    )

    return fingerprint, unavailable


def _configuration_fingerprint(
    memory_path: Path,
) -> str:
    data = _read(
        memory_path / "configuration.json"
    )

    direct = data.get(
        "configuration_fingerprint"
    )

    if direct:
        return str(direct)

    current = _mapping(
        data.get("current")
    )

    current_fingerprint = current.get(
        "configuration_fingerprint"
    )

    if current_fingerprint:
        return str(current_fingerprint)

    snapshot = _mapping(
        current.get("snapshot")
    )

    return str(
        snapshot.get(
            "configuration_fingerprint",
            "missing",
        )
    )


def load_context(
    memory_path: Path,
    target: str | None,
    cwd: Path,
) -> PlanningContext:
    workspaces = _read(
        memory_path / "workspaces.json"
    )

    (
        root,
        workspace_identity,
        target_name,
    ) = _resolve_target(
        workspaces,
        target,
        cwd,
    )

    target_identity = _identity(root)

    discovery = _load_discovery(
        memory_path,
        workspace_identity,
        target_identity,
    )
    project_index = _load_index(
        memory_path,
        workspace_identity,
        target_identity,
    )
    graph = _load_graph(
        memory_path,
        workspace_identity,
        target_identity,
    )

    (
        graph_is_current,
        graph_staleness_reason,
    ) = _graph_freshness(
        project_index,
        graph,
    )

    (
        diagnostic_status,
        diagnostic_fingerprint,
        diagnostic_target_matches,
    ) = _diagnostics(
        memory_path,
        workspace_identity,
        target_identity,
    )

    (
        capability_fingerprint,
        unavailable_capabilities,
    ) = _capabilities(memory_path)

    configuration_fingerprint = (
        _configuration_fingerprint(
            memory_path
        )
    )

    return PlanningContext(
        target_identity=target_identity,
        target_name=target_name,
        workspace_identity=workspace_identity,
        discovery=discovery,
        project_index=project_index,
        graph=graph,
        graph_is_current=graph_is_current,
        graph_staleness_reason=(
            graph_staleness_reason
        ),
        diagnostic_status=diagnostic_status,
        diagnostic_fingerprint=(
            diagnostic_fingerprint
        ),
        diagnostic_target_matches=(
            diagnostic_target_matches
        ),
        capability_fingerprint=(
            capability_fingerprint
        ),
        configuration_fingerprint=(
            configuration_fingerprint
        ),
        unavailable_capabilities=(
            unavailable_capabilities
        ),
    )


