"""Mission engineering-context assembly."""

from __future__ import annotations

from dataclasses import dataclass

from forge.capabilities import CapabilityRegistryQuery
from forge.mission_runtime.capability_resolution import (
    MissionCapabilityResolver,
)
from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.models import MissionRequest
from forge.mission_runtime.workspace_context import (
    build_workspace_context,
    resolve_workspace,
)
from forge.workspace.manager import WorkspaceManager


@dataclass(frozen=True, slots=True)
class MissionContextBuilder:
    """Build repository-grounded context for one mission."""

    workspace_manager: WorkspaceManager
    capability_query: CapabilityRegistryQuery

    def build(
        self,
        request: MissionRequest,
    ) -> MissionEngineeringContext:
        workspace = resolve_workspace(
            manager=self.workspace_manager,
            workspace_id=request.workspace_id,
            repository_root=request.repository_root,
        )
        workspace_context = build_workspace_context(
            workspace
        )
        capability_selection = MissionCapabilityResolver(
            self.capability_query
        ).resolve(
            workspace_context.technology
        )

        references = (
            f"workspace:{workspace.workspace_id}",
            f"repository:{workspace_context.repository_root}",
            *(
                f"capability:{capability_id}"
                for capability_id
                in capability_selection.capability_ids
            ),
        )

        return MissionEngineeringContext(
            workspace=workspace_context,
            capabilities=capability_selection,
            context_references=references,
        )