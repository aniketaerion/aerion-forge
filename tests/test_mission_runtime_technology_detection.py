from pathlib import Path

from forge.mission_runtime.technology_detection import (
    technology_context_from_workspace,
)
from forge.workspace.models import ProjectType, Workspace


def test_workspace_technology_context_is_deterministic(
    tmp_path: Path,
) -> None:
    workspace = Workspace(
        workspace_id="workspace-1",
        name="ERP",
        repository_path=tmp_path,
        project_type=ProjectType.ERP,
        technologies=["Node", "React", "Node"],
        primary_language="TypeScript",
        framework="React",
        database="PostgreSQL",
        git_enabled=True,
    )

    context = technology_context_from_workspace(
        workspace
    )

    assert context.project_type is ProjectType.ERP
    assert context.technologies == ("Node", "React")
    assert context.database == "PostgreSQL"