from pathlib import Path

from forge.memory import JsonMemoryStore


def test_memory_persists_and_appends(tmp_path: Path) -> None:
    path = tmp_path / "memory.json"
    store = JsonMemoryStore(path)
    store.set("architecture_map", {"backend": ["server.py"]})
    store.append("completed_tasks", {"task": "audit"})
    reloaded = JsonMemoryStore(path)
    assert reloaded.read("architecture_map") == {"backend": ["server.py"]}
    assert reloaded.read("completed_tasks") == [{"task": "audit"}]
