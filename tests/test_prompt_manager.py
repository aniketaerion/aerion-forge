from pathlib import Path

import pytest

from forge.prompts import PromptManager


def test_prompt_render_is_strict(tmp_path: Path) -> None:
    (tmp_path / "test.txt").write_text("Hello ${name}", encoding="utf-8")
    manager = PromptManager(tmp_path)
    assert manager.render("test.txt", {"name": "Aerion"}) == "Hello Aerion"
    with pytest.raises(ValueError):
        manager.render("test.txt", {})


def test_prompt_cannot_escape_root(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        PromptManager(tmp_path).load("../secret.txt")
