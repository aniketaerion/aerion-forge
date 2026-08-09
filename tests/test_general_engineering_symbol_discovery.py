from forge.general_engineering.repository_scanner import ScannedRepositoryFile
from forge.general_engineering.symbol_discovery import discover_symbols


def test_python_symbol_discovery_is_read_only_and_structured() -> None:
    file = ScannedRepositoryFile(
        path="src/service.py",
        size_bytes=50,
        suffix=".py",
        fingerprint="abc",
        content="class AccountService:\n    def validate(self):\n        return True\n",
    )
    symbols = discover_symbols(file)
    assert {item.name for item in symbols} == {"AccountService", "validate"}