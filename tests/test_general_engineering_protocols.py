from typing import get_type_hints

from forge.general_engineering.protocols import EngineeringProvider


def test_provider_protocol_exposes_reasoning_only_operations() -> None:
    assert hasattr(EngineeringProvider, "understand_request")
    assert hasattr(EngineeringProvider, "propose_change_plan")
    assert hasattr(EngineeringProvider, "synthesize_edits")
    assert hasattr(EngineeringProvider, "propose_repair")

    forbidden = {
        "write_file",
        "delete_file",
        "run_shell",
        "execute_shell",
        "approve",
        "release",
    }
    assert forbidden.isdisjoint(set(dir(EngineeringProvider)))


def test_provider_protocol_uses_typed_contracts() -> None:
    hints = get_type_hints(
        EngineeringProvider.synthesize_edits,
    )

    assert hints["return"].__name__ == "GeneratedChangeSet"