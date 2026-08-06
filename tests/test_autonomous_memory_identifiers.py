from forge.autonomous_memory.identifiers import (
    memory_observation_identifier,
    memory_record_identifier,
)


def test_memory_identifier_is_stable() -> None:
    first = memory_record_identifier(
        {
            "repository": "repo",
            "statement": "Fact",
        }
    )
    second = memory_record_identifier(
        {
            "statement": "Fact",
            "repository": "repo",
        }
    )

    assert first == second
    assert first.startswith("memory-record-")


def test_observation_identifier_has_prefix() -> None:
    result = memory_observation_identifier(
        {"source_reference": "source-1"}
    )

    assert result.startswith("memory-observation-")