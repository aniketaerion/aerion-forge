"""Request-understanding service for M5.9 Package 1."""

from __future__ import annotations

from dataclasses import dataclass

from forge.general_engineering.errors import EngineeringContractError
from forge.general_engineering.models import (
    ChangeSpecification,
    EngineeringRequest,
)
from forge.general_engineering.requirement_extractor import (
    extract_change_requirements,
)


@dataclass(frozen=True)
class RequestUnderstandingResult:
    """Normalized request plus deterministic change specification."""

    request: EngineeringRequest
    specification: ChangeSpecification


class EngineeringRequestUnderstandingService:
    """Convert a normalized request into a generic change specification.

    Package 1 is deliberately repository-independent. Repository grounding is
    introduced in Package 2.
    """

    def understand(
        self,
        request: EngineeringRequest,
    ) -> RequestUnderstandingResult:
        requirements = extract_change_requirements(
            objective=request.objective,
            acceptance_criteria=request.acceptance_criteria,
        )

        if not requirements:
            raise EngineeringContractError(
                "Engineering request produced no actionable requirements."
            )

        invariants = tuple(
            item
            for item in request.constraints
            if item.casefold().startswith(
                (
                    "do not ",
                    "must not ",
                    "preserve ",
                    "keep ",
                    "only ",
                )
            )
        )

        specification = ChangeSpecification(
            request_id=request.request_id,
            requirements=requirements,
            constraints=request.constraints,
            invariants=invariants,
        )

        return RequestUnderstandingResult(
            request=request,
            specification=specification,
        )


engineering_request_understanding_service = (
    EngineeringRequestUnderstandingService()
)