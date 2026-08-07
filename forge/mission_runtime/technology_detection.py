"""Technology context extraction from Forge workspace metadata."""

from __future__ import annotations

from forge.mission_runtime.context import MissionTechnologyContext
from forge.workspace.models import Workspace


def technology_context_from_workspace(
    workspace: Workspace,
) -> MissionTechnologyContext:
    """Convert validated workspace detection into mission context."""
    technologies = tuple(
        sorted(
            {
                technology.strip()
                for technology in workspace.technologies
                if technology.strip()
            },
            key=str.casefold,
        )
    )

    return MissionTechnologyContext(
        project_type=workspace.project_type,
        technologies=technologies,
        primary_language=workspace.primary_language,
        framework=workspace.framework,
        database=workspace.database,
        package_manager=workspace.package_manager,
        build_system=workspace.build_system,
        test_framework=workspace.test_framework,
        docker_enabled=workspace.docker_enabled,
        git_enabled=workspace.git_enabled,
    )