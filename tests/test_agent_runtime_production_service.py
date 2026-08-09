from forge.agent_runtime.models import AgentCapability
from forge.agent_runtime.production_service import PRODUCTION_CAPABILITIES, production_agent_service


def test_production_service_registers_required_capabilities() -> None:
    service = production_agent_service()
    assert set(service.registry.capabilities()) == set(PRODUCTION_CAPABILITIES)
    assert AgentCapability.SAFE_CODE_EDITING in PRODUCTION_CAPABILITIES
    assert AgentCapability.BUILD_VERIFICATION in PRODUCTION_CAPABILITIES
    assert service.policy.allow_code_changes