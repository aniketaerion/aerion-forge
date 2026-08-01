"""Deterministic safe configuration reports."""

import json

from forge.configuration.models import ConfigurationSnapshot


def _json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, default=str) + "\n"


class ConfigurationRenderer:
    def render(self, snapshot: ConfigurationSnapshot) -> dict[str, str]:
        settings = [x.model_dump(mode="json") for x in snapshot.settings]
        validation = snapshot.validation.model_dump(mode="json")
        changes = snapshot.changes.model_dump(mode="json")
        return {
            "CONFIGURATION_EFFECTIVE.json": _json(
                {
                    "schema_version": snapshot.schema_version,
                    "active_profile": snapshot.active_profile,
                    "configuration_fingerprint": snapshot.configuration_fingerprint,
                    "generation": snapshot.generation.model_dump(mode="json"),
                    "settings": settings,
                }
            ),
            "CONFIGURATION_SOURCES.json": _json(
                {
                    x.key: {
                        "source": x.source,
                        "source_reference": x.source_reference,
                        "is_overridden": x.is_overridden,
                    }
                    for x in snapshot.settings
                }
            ),
            "CONFIGURATION_VALIDATION.json": _json(validation),
            "CONFIGURATION_CHANGES.json": _json(changes),
            "CONFIGURATION_SUMMARY.md": self.summary(snapshot),
            "CONFIGURATION_VALIDATION.md": self.validation(snapshot),
        }

    @staticmethod
    def summary(snapshot: ConfigurationSnapshot) -> str:
        rows = "\n".join(
            f"| `{x.key}` | `{x.safe_value}` | {x.source.value} | "
            f"{'default' if x.is_default else 'override'} |"
            for x in snapshot.settings
        )
        return "\n".join(
            (
                "# Configuration Summary",
                "",
                f"- Profile: `{snapshot.active_profile.value}`",
                f"- Generation: `{snapshot.generation.generation_id}`",
                f"- Fingerprint: `{snapshot.configuration_fingerprint}`",
                f"- Settings: {snapshot.statistics.total_settings}",
                "",
                "| Key | Safe Value | Source | State |",
                "|---|---|---|---|",
                rows,
                "",
            )
        )

    @staticmethod
    def validation(snapshot: ConfigurationSnapshot) -> str:
        rows = (
            "\n".join(
                f"- {x.severity.value}: {x.key or 'configuration'}: {x.message}"
                for x in snapshot.validation.messages
            )
            or "No validation messages."
        )
        valid = "yes" if snapshot.validation.valid else "no"
        return f"# Configuration Validation\n\n- Valid: {valid}\n\n{rows}\n"
