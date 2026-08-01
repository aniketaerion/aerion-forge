"""Unified configuration orchestration."""

from collections.abc import Mapping
from pathlib import Path

from forge.configuration.errors import ConfigurationReportError
from forge.configuration.models import ConfigurationResult, ConfigurationSnapshot
from forge.configuration.renderer import ConfigurationRenderer
from forge.configuration.resolver import ConfigurationResolver
from forge.configuration.store import ConfigurationRepository


class ConfigurationService:
    def __init__(
        self,
        root: Path,
        memory_path: Path,
        reports_path: Path,
        history_limit: int = 5,
        renderer: ConfigurationRenderer | None = None,
    ) -> None:
        self.root = root.resolve()
        self.store = ConfigurationRepository(memory_path / "configuration.json", history_limit)
        self.reports_path = reports_path.resolve()
        self.renderer = renderer or ConfigurationRenderer()

    def resolve(
        self,
        *,
        profile: str | None = None,
        config_file: Path | None = None,
        environment: Mapping[str, str] | None = None,
        overrides: tuple[str, ...] = (),
        persist: bool = True,
    ) -> ConfigurationResult:
        previous = self.store.load().snapshot
        snapshot = ConfigurationResolver(self.root).resolve(
            profile=profile,
            config_file=config_file,
            environment=environment,
            overrides=overrides,
            previous=previous,
        )
        self._reports(snapshot)
        if persist:
            self.store.save(snapshot)
        return ConfigurationResult(snapshot=snapshot)

    def _reports(self, snapshot: ConfigurationSnapshot) -> None:
        self.reports_path.mkdir(parents=True, exist_ok=True)
        staged = []
        try:
            for name, content in self.renderer.render(snapshot).items():
                destination = (self.reports_path / name).resolve()
                if self.reports_path not in destination.parents:
                    raise ConfigurationReportError(
                        "Configuration report path escapes output directory."
                    )
                temp = destination.with_suffix(destination.suffix + ".tmp")
                temp.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
                staged.append((temp, destination))
            for temp, destination in staged:
                temp.replace(destination)
        except (OSError, ConfigurationReportError) as exc:
            for temp, _ in staged:
                temp.unlink(missing_ok=True)
            if isinstance(exc, ConfigurationReportError):
                raise
            raise ConfigurationReportError("Unable to write configuration reports.") from exc
