import json
from pathlib import Path

import pytest

from forge.discovery import DiscoveryError, RepositoryDiscoveryScanner
from forge.discovery.renderer import DiscoveryRenderer


def write(path: Path, content: str = "") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_discovers_python_repository(tmp_path: Path) -> None:
    write(
        tmp_path / "pyproject.toml",
        '[project]\nname = "sample"\ndependencies = ["psycopg>=3"]\n'
        "[tool.pytest.ini_options]\n[tool.ruff]\n[tool.mypy]\n",
    )
    write(tmp_path / "src" / "sample.py", "print('not parsed')\n")

    result = RepositoryDiscoveryScanner(tmp_path).scan()

    assert result.project_type == "Python"
    assert result.languages == {"Python": 1}
    assert {"pytest"} == set(result.test_frameworks)
    assert {"ruff", "mypy"} == set(result.linting)
    assert "PostgreSQL" in result.databases


def test_discovers_react_repository(tmp_path: Path) -> None:
    write(
        tmp_path / "package.json",
        json.dumps(
            {
                "dependencies": {"react": "19.0.0"},
                "devDependencies": {"typescript": "5", "vitest": "3", "prettier": "3"},
                "scripts": {"build": "vite build"},
            }
        ),
    )
    write(tmp_path / "tsconfig.json", "{}")
    write(tmp_path / "src" / "App.tsx", "export default 1")

    result = RepositoryDiscoveryScanner(tmp_path).scan()

    assert result.project_type == "React"
    assert {"React", "Node", "TypeScript"} <= set(result.technologies)
    assert result.test_frameworks == ["vitest"]
    assert result.formatting == ["prettier"]
    assert result.applications[0].kind == "frontend application"


def test_discovers_node_repository(tmp_path: Path) -> None:
    write(
        tmp_path / "package.json",
        json.dumps(
            {
                "dependencies": {"express": "5", "redis": "5", "graphql": "16"},
                "devDependencies": {"jest": "30", "eslint": "9"},
            }
        ),
    )
    write(tmp_path / "package-lock.json", "{}")

    result = RepositoryDiscoveryScanner(tmp_path).scan()

    assert result.project_type == "Express"
    assert {"Express", "GraphQL", "Redis"} <= set(result.technologies)
    assert result.package_managers == ["npm"]
    assert result.test_frameworks == ["jest"]
    assert result.linting == ["eslint"]


def test_discovers_mixed_repository(tmp_path: Path) -> None:
    write(tmp_path / "requirements.txt", "pytest>=8\n")
    write(tmp_path / "backend.py", "value = 1\n")
    write(tmp_path / "go.mod", "module example.test/service\n")
    write(tmp_path / "service" / "main.go", "package main\n")
    write(tmp_path / ".github" / "workflows" / "ci.yml", "name: ci\n")

    result = RepositoryDiscoveryScanner(tmp_path).scan()

    assert {"Python", "Go"} <= set(result.technologies)
    assert result.languages == {"Go": 1, "Python": 1}
    assert result.ci_cd == ["GitHub Actions"]


def test_discovers_docker_and_kubernetes_repository(tmp_path: Path) -> None:
    write(tmp_path / "Dockerfile", "FROM alpine\n")
    write(tmp_path / "compose.yaml", "services: {}\n")
    write(tmp_path / "k8s" / "deployment.yaml", "kind: Deployment\n")

    result = RepositoryDiscoveryScanner(tmp_path).scan()

    assert result.docker
    assert result.docker_compose
    assert result.kubernetes_manifests == ["k8s/deployment.yaml"]


def test_discovers_monorepo_applications_services_and_libraries(tmp_path: Path) -> None:
    write(tmp_path / "apps" / "web" / "package.json", '{"dependencies":{"next":"15"}}')
    write(tmp_path / "services" / "api" / "package.json", '{"dependencies":{"express":"5"}}')
    write(tmp_path / "packages" / "shared" / "package.json", "{}")

    result = RepositoryDiscoveryScanner(tmp_path).scan()
    kinds = {application.path: application.kind for application in result.applications}

    assert kinds["apps/web"] == "frontend application"
    assert kinds["services/api"] == "backend service"
    assert kinds["packages/shared"] == "library"
    assert result.microservices == ["services/api"]
    assert result.libraries == ["packages/shared"]


def test_empty_repository_has_deterministic_empty_metadata(tmp_path: Path) -> None:
    result = RepositoryDiscoveryScanner(tmp_path).scan()
    first = DiscoveryRenderer().render(result)
    second = DiscoveryRenderer().render(RepositoryDiscoveryScanner(tmp_path).scan())

    assert result.project_type == "Generic"
    assert result.file_count == 0
    assert result.applications == []
    assert first == second


def test_broken_repository_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(DiscoveryError, match="does not exist"):
        RepositoryDiscoveryScanner(tmp_path / "missing").scan()
