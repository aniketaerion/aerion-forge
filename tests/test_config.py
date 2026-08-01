from pathlib import Path

import pytest

from forge.config import Settings


def test_settings_resolve_paths(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings(
        repository_path=Path("repo"),
        reports_path=Path("output"),
        _env_file=None,  # type: ignore[call-arg]
    )
    assert settings.repository_path == (tmp_path / "repo").resolve()
    assert settings.reports_path == (tmp_path / "output").resolve()


def test_invalid_log_level_is_rejected() -> None:
    with pytest.raises(ValueError):
        Settings(log_level="verbose", _env_file=None)  # type: ignore[call-arg]


def test_runtime_path_defaults_are_separated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    assert settings.workspace_path == tmp_path / "workspaces"
    assert settings.reports_path == tmp_path / "reports" / "latest"
