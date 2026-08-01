"""Deterministic discovery artifact rendering."""

import json

from forge.discovery.models import DiscoveryResult


def _json(data: object) -> str:
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n"


def _items(values: list[str]) -> str:
    return "\n".join(f"- `{value}`" for value in values) if values else "None detected."


class DiscoveryRenderer:
    """Render structured JSON artifacts and human-readable summaries."""

    def render(self, result: DiscoveryResult) -> dict[str, str]:
        """Return every required artifact keyed by deterministic filename."""
        data = result.model_dump(mode="json")
        project = {
            key: data[key]
            for key in (
                "repository_name",
                "project_type",
                "repository_size_bytes",
                "file_count",
                "directory_count",
                "license_file",
                "git",
                "workspace_compatible",
            )
        }
        technology = {
            key: data[key]
            for key in (
                "languages",
                "frameworks",
                "technologies",
                "databases",
                "package_managers",
                "docker",
                "docker_compose",
                "ci_cd",
            )
        }
        applications = {key: data[key] for key in ("applications", "libraries", "microservices")}
        build = {key: data[key] for key in ("build_systems", "scripts")}
        testing = {key: data[key] for key in ("test_frameworks", "linting", "formatting")}
        configuration = {
            key: data[key]
            for key in (
                "configuration_files",
                "environment_files",
                "documentation",
                "kubernetes_manifests",
            )
        }
        return {
            "PROJECT.json": _json(project),
            "TECH_STACK.json": _json(technology),
            "APPLICATIONS.json": _json(applications),
            "DEPENDENCIES.json": _json({"dependencies": data["dependencies"]}),
            "BUILD_SYSTEM.json": _json(build),
            "TEST_FRAMEWORKS.json": _json(testing),
            "CONFIGURATION.json": _json(configuration),
            "DIRECTORY_STRUCTURE.json": _json({"directories": data["directory_structure"]}),
            "PROJECT_SUMMARY.md": self._project_summary(result),
            "TECHNOLOGY_SUMMARY.md": self._technology_summary(result),
            "APPLICATION_SUMMARY.md": self._application_summary(result),
        }

    @staticmethod
    def _project_summary(result: DiscoveryResult) -> str:
        return f"""# Project Summary

- Repository: `{result.repository_name}`
- Project type: {result.project_type}
- Files: {result.file_count}
- Directories: {result.directory_count}
- Size: {result.repository_size_bytes} bytes
- Git: {"yes" if result.git else "no"}
- Workspace compatible: {"yes" if result.workspace_compatible else "no"}
"""

    @staticmethod
    def _technology_summary(result: DiscoveryResult) -> str:
        languages = [f"{name}: {count} files" for name, count in result.languages.items()]
        return f"""# Technology Summary

## Technologies

{_items(result.technologies)}

## Languages

{_items(languages)}

## Build Systems

{_items(result.build_systems)}

## Testing

{_items(result.test_frameworks)}
"""

    @staticmethod
    def _application_summary(result: DiscoveryResult) -> str:
        applications = [
            f"{application.kind}: {application.name} ({application.path})"
            for application in result.applications
        ]
        return f"""# Application Summary

## Applications and Services

{_items(applications)}

## Shared Libraries

{_items(result.libraries)}

## Microservices

{_items(result.microservices)}
"""
