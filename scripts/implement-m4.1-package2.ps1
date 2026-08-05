[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Write-Utf8NoBom {
    param(
        [Parameter(Mandatory)][string]$Path,
        [Parameter(Mandatory)][string]$Content
    )

    $FullPath = Join-Path $RepositoryRoot $Path
    $Directory = Split-Path $FullPath -Parent
    New-Item -ItemType Directory -Path $Directory -Force | Out-Null

    [System.IO.File]::WriteAllText(
        $FullPath,
        $Content,
        [System.Text.UTF8Encoding]::new($false)
    )

    Write-Host "WROTE $Path" -ForegroundColor Green
}

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

Write-Utf8NoBom "forge\domain_intelligence\frontend\components.py" @'
"""Component discovery for M4.1 Frontend Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
)

_COMPONENT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bfunction\s+([A-Z][A-Za-z0-9_]*)\s*\("),
    re.compile(r"\bclass\s+([A-Z][A-Za-z0-9_]*)\s+extends\s+React\.Component"),
    re.compile(r"\bconst\s+([A-Z][A-Za-z0-9_]*)\s*=\s*(?:\([^)]*\)|[A-Za-z0-9_]+)\s*=>"),
)

_COMPONENT_SUFFIXES = {".jsx", ".tsx"}


def discover_component_files(project_root: Path) -> tuple[Path, ...]:
    """Return deterministic React component source files."""
    files = [
        path
        for path in project_root.rglob("*")
        if path.is_file()
        and path.suffix.lower() in _COMPONENT_SUFFIXES
        and "node_modules" not in path.parts
        and "dist" not in path.parts
        and "build" not in path.parts
        and ".next" not in path.parts
    ]

    return tuple(sorted(files, key=lambda path: path.as_posix()))


def extract_component_names(source: str) -> tuple[str, ...]:
    """Extract likely component names without executing source code."""
    names: set[str] = set()

    for pattern in _COMPONENT_PATTERNS:
        names.update(pattern.findall(source))

    return tuple(sorted(names))


def component_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce one finding per discovered component file."""
    findings: list[FrontendFinding] = []

    for path in discover_component_files(project_root):
        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        names = extract_component_names(source)

        if not names:
            continue

        relative = path.relative_to(project_root).as_posix()
        finding_id = frontend_finding_identifier(
            {
                "category": "component",
                "path": relative,
                "names": names,
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="component",
                severity=FrontendFindingSeverity.INFO,
                message=f"React component file detected: {relative}",
                path=relative,
                evidence={
                    "component_count": str(len(names)),
                    "components": ",".join(names),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\routing.py" @'
"""Routing discovery for M4.1 Frontend Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
)

_ROUTE_PATTERN = re.compile(
    r"<Route\b[^>]*\bpath\s*=\s*[\"']([^\"']+)[\"']",
    re.IGNORECASE,
)

_NEXT_ROUTE_FILES = {
    "page.js",
    "page.jsx",
    "page.ts",
    "page.tsx",
    "route.js",
    "route.ts",
}


def discover_route_files(project_root: Path) -> tuple[Path, ...]:
    """Return route configuration and convention-based route files."""
    candidates: set[Path] = set()

    for path in project_root.rglob("*"):
        if not path.is_file():
            continue

        if any(
            excluded in path.parts
            for excluded in ("node_modules", "dist", "build", ".next")
        ):
            continue

        if path.name in _NEXT_ROUTE_FILES:
            candidates.add(path)
            continue

        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        if "<Route" in source or "createBrowserRouter" in source:
            candidates.add(path)

    return tuple(sorted(candidates, key=lambda path: path.as_posix()))


def extract_route_paths(source: str) -> tuple[str, ...]:
    """Extract explicit React Router paths."""
    return tuple(sorted(set(_ROUTE_PATTERN.findall(source))))


def route_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce findings for explicit and convention-based routes."""
    findings: list[FrontendFinding] = []

    for path in discover_route_files(project_root):
        relative = path.relative_to(project_root).as_posix()

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            source = ""

        routes = extract_route_paths(source)

        if not routes and path.name in _NEXT_ROUTE_FILES:
            routes = (relative,)

        finding_id = frontend_finding_identifier(
            {
                "category": "routing",
                "path": relative,
                "routes": routes,
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="routing",
                severity=FrontendFindingSeverity.INFO,
                message=f"Frontend routing detected: {relative}",
                path=relative,
                evidence={
                    "route_count": str(len(routes)),
                    "routes": ",".join(routes),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\hooks.py" @'
"""React hook usage discovery for M4.1 Frontend Intelligence."""

from __future__ import annotations

import re
from pathlib import Path

from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
)

_HOOK_PATTERN = re.compile(r"\b(use[A-Z][A-Za-z0-9_]*)\s*\(")


def extract_hook_names(source: str) -> tuple[str, ...]:
    """Extract built-in and custom React hook names."""
    return tuple(sorted(set(_HOOK_PATTERN.findall(source))))


def hook_findings(project_root: Path) -> tuple[FrontendFinding, ...]:
    """Produce findings for files that use React hooks."""
    findings: list[FrontendFinding] = []

    for path in sorted(
        project_root.rglob("*"),
        key=lambda item: item.as_posix(),
    ):
        if not path.is_file():
            continue

        if path.suffix.lower() not in {".js", ".jsx", ".ts", ".tsx"}:
            continue

        if any(
            excluded in path.parts
            for excluded in ("node_modules", "dist", "build", ".next")
        ):
            continue

        try:
            source = path.read_text(encoding="utf-8-sig")
        except OSError:
            continue

        hooks = extract_hook_names(source)

        if not hooks:
            continue

        relative = path.relative_to(project_root).as_posix()
        finding_id = frontend_finding_identifier(
            {
                "category": "hooks",
                "path": relative,
                "hooks": hooks,
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="hooks",
                severity=FrontendFindingSeverity.INFO,
                message=f"React hook usage detected: {relative}",
                path=relative,
                evidence={
                    "hook_count": str(len(hooks)),
                    "hooks": ",".join(hooks),
                },
            )
        )

    return tuple(
        sorted(findings, key=lambda finding: finding.finding_id)
    )
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\state_management.py" @'
"""Frontend state-management discovery for M4.1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.react import (
    load_package_json,
    package_dependencies,
)
from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
)

_STATE_PACKAGES: dict[str, str] = {
    "@reduxjs/toolkit": "redux-toolkit",
    "redux": "redux",
    "zustand": "zustand",
    "mobx": "mobx",
    "jotai": "jotai",
    "recoil": "recoil",
    "xstate": "xstate",
}


def detect_state_management(project_root: Path) -> tuple[str, ...]:
    """Detect common state-management libraries."""
    dependencies = package_dependencies(
        load_package_json(project_root)
    )

    detected = {
        label
        for package_name, label in _STATE_PACKAGES.items()
        if package_name in dependencies
    }

    return tuple(sorted(detected))


def state_management_findings(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    """Produce deterministic findings for detected state libraries."""
    findings: list[FrontendFinding] = []

    for library in detect_state_management(project_root):
        finding_id = frontend_finding_identifier(
            {
                "category": "state_management",
                "library": library,
                "root": project_root.as_posix(),
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="state_management",
                severity=FrontendFindingSeverity.INFO,
                message=f"State-management library detected: {library}",
                path="package.json",
                evidence={"library": library},
            )
        )

    return tuple(findings)
'@

Write-Utf8NoBom "forge\domain_intelligence\frontend\styling.py" @'
"""Frontend styling discovery for M4.1."""

from __future__ import annotations

from pathlib import Path

from forge.domain_intelligence.frontend.react import (
    load_package_json,
    package_dependencies,
)
from forge.domain_intelligence.identifiers import (
    frontend_finding_identifier,
)
from forge.domain_intelligence.models import (
    FrontendFinding,
    FrontendFindingSeverity,
)

_STYLE_PACKAGES: dict[str, str] = {
    "tailwindcss": "tailwindcss",
    "styled-components": "styled-components",
    "@emotion/react": "emotion",
    "sass": "sass",
    "less": "less",
    "@mui/material": "mui",
    "bootstrap": "bootstrap",
}


def detect_styling_technologies(
    project_root: Path,
) -> tuple[str, ...]:
    """Detect styling libraries and source conventions."""
    dependencies = package_dependencies(
        load_package_json(project_root)
    )

    detected = {
        label
        for package_name, label in _STYLE_PACKAGES.items()
        if package_name in dependencies
    }

    if any(project_root.rglob("*.module.css")):
        detected.add("css-modules")

    if any(project_root.rglob("*.scss")):
        detected.add("scss")

    if any(project_root.rglob("*.css")):
        detected.add("css")

    return tuple(sorted(detected))


def styling_findings(
    project_root: Path,
) -> tuple[FrontendFinding, ...]:
    """Produce deterministic findings for styling technologies."""
    findings: list[FrontendFinding] = []

    for technology in detect_styling_technologies(project_root):
        finding_id = frontend_finding_identifier(
            {
                "category": "styling",
                "technology": technology,
                "root": project_root.as_posix(),
            }
        )

        findings.append(
            FrontendFinding(
                finding_id=finding_id,
                category="styling",
                severity=FrontendFindingSeverity.INFO,
                message=f"Styling technology detected: {technology}",
                evidence={"technology": technology},
            )
        )

    return tuple(findings)
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_components.py" @'
from pathlib import Path

from forge.domain_intelligence.frontend.components import (
    component_findings,
    extract_component_names,
)


def test_extract_component_names() -> None:
    source = """
    function Dashboard() { return <div /> }
    const StatusCard = () => <section />
    """

    assert extract_component_names(source) == (
        "Dashboard",
        "StatusCard",
    )


def test_component_findings_include_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "src"
    source.mkdir()
    (source / "Dashboard.tsx").write_text(
        "export function Dashboard() { return <div /> }",
        encoding="utf-8",
    )

    findings = component_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "src/Dashboard.tsx"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_routing.py" @'
from pathlib import Path

from forge.domain_intelligence.frontend.routing import (
    extract_route_paths,
    route_findings,
)


def test_extract_route_paths() -> None:
    source = """
    <Route path="/dashboard" element={<Dashboard />} />
    <Route path="/settings" element={<Settings />} />
    """

    assert extract_route_paths(source) == (
        "/dashboard",
        "/settings",
    )


def test_nextjs_page_is_discovered(tmp_path: Path) -> None:
    page = tmp_path / "app" / "dashboard"
    page.mkdir(parents=True)
    (page / "page.tsx").write_text(
        "export default function Page() { return <div /> }",
        encoding="utf-8",
    )

    findings = route_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].path == "app/dashboard/page.tsx"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_hooks.py" @'
from pathlib import Path

from forge.domain_intelligence.frontend.hooks import (
    extract_hook_names,
    hook_findings,
)


def test_extract_hook_names() -> None:
    source = """
    const [value, setValue] = useState(0)
    const mission = useMission()
    useEffect(() => {}, [])
    """

    assert extract_hook_names(source) == (
        "useEffect",
        "useMission",
        "useState",
    )


def test_hook_findings_include_custom_hooks(
    tmp_path: Path,
) -> None:
    path = tmp_path / "Component.tsx"
    path.write_text(
        "export const Component = () => { useMission(); return null }",
        encoding="utf-8",
    )

    findings = hook_findings(tmp_path)

    assert len(findings) == 1
    assert findings[0].evidence["hooks"] == "useMission"
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_state_management.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.frontend.state_management import (
    detect_state_management,
)


def test_detect_state_management(tmp_path: Path) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "dependencies": {
                    "@reduxjs/toolkit": "^2.0.0",
                    "zustand": "^5.0.0",
                }
            }
        ),
        encoding="utf-8",
    )

    assert detect_state_management(tmp_path) == (
        "redux-toolkit",
        "zustand",
    )
'@

Write-Utf8NoBom "tests\test_domain_intelligence_frontend_styling.py" @'
import json
from pathlib import Path

from forge.domain_intelligence.frontend.styling import (
    detect_styling_technologies,
)


def test_detect_styling_packages_and_files(
    tmp_path: Path,
) -> None:
    (tmp_path / "package.json").write_text(
        json.dumps(
            {
                "devDependencies": {
                    "tailwindcss": "^4.0.0",
                }
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "app.module.css").write_text(
        ".root {}",
        encoding="utf-8",
    )

    assert detect_styling_technologies(tmp_path) == (
        "css",
        "css-modules",
        "tailwindcss",
    )
'@

Write-Host ""
Write-Host "M4.1 Package 2 files written. Running validation..." -ForegroundColor Cyan

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest `
    .\tests\test_domain_intelligence_frontend_components.py `
    .\tests\test_domain_intelligence_frontend_routing.py `
    .\tests\test_domain_intelligence_frontend_hooks.py `
    .\tests\test_domain_intelligence_frontend_state_management.py `
    .\tests\test_domain_intelligence_frontend_styling.py `
    -p no:cacheprovider
Assert-CommandSuccess "M4.1 Package 2 tests"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

Write-Host ""
Write-Host "M4.1 PACKAGE 2 COMPLETE" -ForegroundColor Green

git status --short