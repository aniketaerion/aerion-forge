"""Validation planning for M5.9 Package 3."""

from __future__ import annotations

from forge.general_engineering.identifiers import validation_plan_identifier
from forge.general_engineering.models import EngineeringRequest, ValidationPlan


def build_validation_plan(
    request: EngineeringRequest,
    target_paths: tuple[str, ...],
) -> ValidationPlan:
    """Build a provider-independent validation intent.

    Package 3 defines validation capabilities only. It does not execute shell
    commands or decide repository-specific commands; execution arrives later.
    """
    capabilities = ["repository_tests", "static_analysis"]
    if any(path.casefold().startswith("tests/") for path in target_paths):
        capabilities.append("focused_tests")

    payload = {
        "request_id": request.request_id,
        "target_paths": target_paths,
        "capabilities": tuple(capabilities),
    }
    return ValidationPlan(
        validation_plan_id=validation_plan_identifier(payload),
        capabilities=tuple(capabilities),
    )