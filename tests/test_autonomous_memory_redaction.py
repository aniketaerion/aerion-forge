import pytest

from forge.autonomous_memory.errors import MemoryRedactionError
from forge.autonomous_memory.redaction import (
    assert_no_prohibited_content,
    redact_prohibited_content,
)


def test_secret_is_redacted() -> None:
    result = redact_prohibited_content(
        "api_key=abcdefghijklmnop"
    )
    assert "REDACTED" in result.content


def test_secret_assertion_rejects() -> None:
    with pytest.raises(MemoryRedactionError):
        assert_no_prohibited_content(
            "password=supersecretvalue"
        )