from forge.domain_intelligence.phase_validation.models import (
    PhaseValidationKind,
)
from forge.domain_intelligence.phase_validation.registry import (
    PhaseValidationRegistry,
)


def test_default_phase_validation_registry() -> None:
    registry = PhaseValidationRegistry.default()

    assert {
        check.kind for check in registry.checks()
    } == {
        PhaseValidationKind.ACCEPTANCE,
        PhaseValidationKind.ARCHITECTURE,
    }