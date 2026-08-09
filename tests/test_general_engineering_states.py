from forge.general_engineering.states import (
    EditOperationType,
    EngineeringRisk,
    ValidationStatus,
)


def test_general_engineering_states_are_stable_string_enums() -> None:
    assert EditOperationType.CREATE_FILE.value == "create_file"
    assert EditOperationType.REPLACE.value == "replace"
    assert EngineeringRisk.CRITICAL.value == "critical"
    assert ValidationStatus.PASSED.value == "passed"