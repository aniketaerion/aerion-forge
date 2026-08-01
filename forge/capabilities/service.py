"""Capability registry construction, reporting, and persistence service."""

from pathlib import Path

from forge.capabilities.catalogue import built_in_catalogue
from forge.capabilities.errors import CapabilityRegistryDisabledError, CapabilityReportError
from forge.capabilities.models import (
    CapabilityDefinition,
    CapabilityRegistryConfiguration,
    CapabilityRegistryResult,
)
from forge.capabilities.registry import CapabilityRegistryBuilder
from forge.capabilities.renderer import CapabilityRegistryRenderer
from forge.capabilities.store import CapabilityRegistryRepository


class CapabilityRegistryService:
    def __init__(
        self,
        store: CapabilityRegistryRepository,
        reports_path: Path,
        configuration: CapabilityRegistryConfiguration,
        renderer: CapabilityRegistryRenderer | None = None,
    ) -> None:
        self.store = store
        self.reports_path = reports_path.resolve()
        self.configuration = configuration
        self.renderer = renderer or CapabilityRegistryRenderer()

    def build(
        self, definitions: tuple[CapabilityDefinition, ...] | None = None
    ) -> CapabilityRegistryResult:
        if not self.configuration.enabled:
            raise CapabilityRegistryDisabledError("Capability registry is disabled")
        previous = self.store.load().registry
        result = CapabilityRegistryBuilder(self.configuration).build(
            definitions or built_in_catalogue(), previous
        )
        self._write_reports(result)
        self.store.save(result.registry)
        return result

    def _write_reports(self, result: CapabilityRegistryResult) -> None:
        self.reports_path.mkdir(parents=True, exist_ok=True)
        staged: list[tuple[Path, Path]] = []
        try:
            for filename, content in self.renderer.render(result).items():
                destination = (self.reports_path / filename).resolve()
                if self.reports_path not in destination.parents:
                    raise CapabilityReportError(
                        "Capability report path escapes configured directory"
                    )
                temporary = destination.with_suffix(destination.suffix + ".tmp")
                temporary.write_text(content.rstrip() + "\n", encoding="utf-8", newline="\n")
                staged.append((temporary, destination))
            for temporary, destination in staged:
                temporary.replace(destination)
        except (OSError, CapabilityReportError) as exc:
            for temporary, _ in staged:
                temporary.unlink(missing_ok=True)
            if isinstance(exc, CapabilityReportError):
                raise
            raise CapabilityReportError(f"Unable to write capability reports: {exc}") from exc
