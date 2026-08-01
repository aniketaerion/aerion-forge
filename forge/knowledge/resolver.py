"""Conservative structural boundaries derived from discovery and index state."""

from dataclasses import dataclass
from pathlib import PurePosixPath

from forge.discovery.models import DiscoveryResult
from forge.indexing.models import IndexedFile
from forge.knowledge.identifiers import normalize_path
from forge.knowledge.models import KnowledgeNodeType


@dataclass(frozen=True)
class ComponentBoundary:
    path: str
    node_type: KnowledgeNodeType
    name: str


@dataclass(frozen=True)
class FilePlacement:
    component_path: str | None
    module_path: str | None
    directory_paths: tuple[str, ...]


class StructuralResolver:
    """Resolve components, bounded modules, and directories without source parsing."""

    def __init__(self, max_module_depth: int) -> None:
        self.max_module_depth = max_module_depth

    def components(self, discovery: DiscoveryResult) -> list[ComponentBoundary]:
        """Convert discovery application classifications into structural boundaries."""
        boundaries: dict[str, ComponentBoundary] = {}
        for application in discovery.applications:
            path = normalize_path(application.path) or "."
            node_type = {
                "backend service": KnowledgeNodeType.SERVICE,
                "library": KnowledgeNodeType.LIBRARY,
            }.get(application.kind, KnowledgeNodeType.APPLICATION)
            boundaries[path] = ComponentBoundary(path, node_type, application.name)
        return sorted(boundaries.values(), key=lambda item: (item.path, item.node_type.value))

    def place(self, file: IndexedFile, components: list[ComponentBoundary]) -> FilePlacement:
        """Place one indexed file using longest-prefix component and bounded path rules."""
        path = normalize_path(file.path)
        parent_parts = PurePosixPath(path).parent.parts
        directories = tuple(
            "/".join(parent_parts[: index + 1]) for index in range(len(parent_parts))
        )
        matches = [
            component
            for component in components
            if component.path != "."
            and (path == component.path or path.startswith(f"{component.path}/"))
        ]
        component = max(matches, key=lambda item: len(item.path)) if matches else None
        base_parts = (
            ()
            if component is None or component.path == "."
            else PurePosixPath(component.path).parts
        )
        remainder = parent_parts[len(base_parts) :]
        module_path = None
        if remainder:
            module_parts = (*base_parts, *remainder[: self.max_module_depth])
            module_path = "/".join(module_parts)
        elif component and component.path != ".":
            module_path = component.path
        return FilePlacement(component.path if component else None, module_path, directories)
