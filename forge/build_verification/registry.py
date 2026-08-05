"""Provider registry for M3.7 Build Verification."""

from __future__ import annotations

from forge.build_verification.errors import BuildVerificationProviderError
from forge.build_verification.models import VerificationTool
from forge.build_verification.providers import (
    BuildVerificationProvider,
    MyPyProvider,
    NodeBuildProvider,
    NodeLintProvider,
    NodeTestProvider,
    PytestProvider,
    PythonBuildProvider,
    RuffProvider,
)


class BuildVerificationProviderRegistry:
    """Deterministic registry keyed by verification tool."""

    def __init__(
        self,
        providers: tuple[BuildVerificationProvider, ...] | None = None,
    ) -> None:
        selected = providers or (
            RuffProvider(),
            MyPyProvider(),
            PytestProvider(),
            PythonBuildProvider(),
            NodeLintProvider(),
            NodeTestProvider(),
            NodeBuildProvider(),
        )

        self._providers = {
            provider.tool: provider
            for provider in selected
        }

        if len(self._providers) != len(selected):
            raise BuildVerificationProviderError(
                "duplicate build verification provider registration"
            )

    def get(
        self,
        tool: VerificationTool,
    ) -> BuildVerificationProvider:
        """Return the provider for one verification tool."""
        try:
            return self._providers[tool]
        except KeyError as exc:
            raise BuildVerificationProviderError(
                f"no provider registered for tool: {tool.value}"
            ) from exc

    def tools(self) -> tuple[VerificationTool, ...]:
        """Return registered tools in deterministic order."""
        return tuple(sorted(self._providers, key=lambda item: item.value))