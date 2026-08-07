"""Mission runtime integration boundary for repository context."""

from __future__ import annotations

from dataclasses import dataclass

from forge.mission_runtime.context import MissionEngineeringContext
from forge.mission_runtime.context_builder import MissionContextBuilder
from forge.mission_runtime.models import MissionRequest


@dataclass(frozen=True, slots=True)
class MissionContextIntegration:
    """Stable integration façade for Package 1."""

    builder: MissionContextBuilder

    def resolve(
        self,
        request: MissionRequest,
    ) -> MissionEngineeringContext:
        return self.builder.build(request)