"""Deterministic capability registry report rendering."""

import json

from forge.capabilities.models import CapabilityRegistryResult


def _json(value: object) -> str:
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, default=str) + "\n"


class CapabilityRegistryRenderer:
    def render(self, result: CapabilityRegistryResult) -> dict[str, str]:
        registry = result.registry
        changes = result.changes
        dependencies = {
            item.capability_id: {
                "required": list(item.required_capabilities),
                "optional": list(item.optional_capabilities),
            }
            for item in registry.definitions
        }
        roadmap = [
            item.model_dump(mode="json")
            for item in registry.definitions
            if item.implementation_status.value == "not_implemented"
        ]
        return {
            "CAPABILITIES.json": _json(registry.model_dump(mode="json")),
            "CAPABILITY_SUMMARY.json": _json(
                {
                    "generation": registry.generation.model_dump(mode="json"),
                    "statistics": registry.statistics.model_dump(mode="json"),
                }
            ),
            "CAPABILITY_CHANGES.json": _json(changes.model_dump(mode="json")),
            "CAPABILITY_DEPENDENCIES.json": _json(dependencies),
            "CAPABILITY_ROADMAP.json": _json({"capabilities": roadmap}),
            "CAPABILITY_SUMMARY.md": self._summary(result),
            "CAPABILITY_CHANGES.md": self._changes(result),
            "CAPABILITY_ROADMAP.md": self._roadmap(result),
        }

    @staticmethod
    def _summary(result: CapabilityRegistryResult) -> str:
        r = result.registry
        evaluations = {item.capability_id: item for item in r.evaluations}
        rows = "\n".join(
            f"| `{d.capability_id}` | {d.display_name} | "
            f"{evaluations[d.capability_id].lifecycle.value} | "
            f"{d.implementation_status.value} | {d.maturity.value} | {d.milestone} |"
            for d in r.definitions
        )
        return "\n".join(
            (
                "# Capability Registry Summary",
                "",
                f"- Generation: `{r.generation.generation_id}`",
                f"- Fingerprint: `{r.generation.registry_fingerprint}`",
                f"- Total: {r.statistics.total_capabilities}",
                f"- Available: {r.statistics.available_capabilities}",
                f"- Planned: {r.statistics.planned_capabilities}",
                "",
                "| ID | Name | Status | Implementation | Maturity | Milestone |",
                "|---|---|---|---|---|---|",
                rows,
                "",
            )
        )

    @staticmethod
    def _changes(result: CapabilityRegistryResult) -> str:
        def section(name: str, values: object) -> str:
            items = values if isinstance(values, tuple) else ()
            body = "\n".join(f"- `{x.capability_id}`" for x in items) or "None."
            return f"## {name}\n{body}"

        c = result.changes
        return (
            "# Capability Registry Changes\n\n"
            + "\n\n".join(
                (
                    section("Added", c.added),
                    section("Modified", c.modified),
                    section("Removed", c.removed),
                    section("Unchanged", c.unchanged),
                )
            )
            + "\n"
        )

    @staticmethod
    def _roadmap(result: CapabilityRegistryResult) -> str:
        values = [
            x
            for x in result.registry.definitions
            if x.implementation_status.value == "not_implemented"
        ]
        return (
            "# Capability Roadmap\n\n"
            + (
                "\n".join(
                    f"- `{x.capability_id}`: planned for Milestone {x.milestone}" for x in values
                )
                or "None."
            )
            + "\n"
        )
