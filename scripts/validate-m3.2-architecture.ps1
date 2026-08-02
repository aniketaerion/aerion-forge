$Files = @(
    "docs\safe_change_planning\ARCHITECTURE.md",
    "docs\safe_change_planning\SPECIFICATION.md",
    "docs\safe_change_planning\DATA_MODEL.md",
    "docs\safe_change_planning\RISK_MODEL.md",
    "docs\safe_change_planning\PLANNING_ALGORITHM.md",
    "docs\safe_change_planning\API_CONTRACT.md",
    "docs\safe_change_planning\TEST_PLAN.md",
    "docs\safe_change_planning\ACCEPTANCE_CRITERIA.md"
)

$Problems = foreach ($File in $Files) {
    if (-not (Test-Path $File)) {
        "MISSING: $File"
    }
    elseif ((Get-Item $File).Length -eq 0) {
        "EMPTY: $File"
    }
}

if ($Problems) {
    $Problems
    throw "M3.2 architecture package is incomplete."
}

$RequiredHeadings = @{
    "ARCHITECTURE.md" = @(
        "# Safe Change Planning Architecture",
        "## Safety boundary",
        "## Components"
    )
    "SPECIFICATION.md" = @(
        "# Safe Change Planning Specification",
        "## Scope",
        "## Functional requirements"
    )
    "DATA_MODEL.md" = @(
        "# Safe Change Planning Data Model",
        "## Entities",
        "## Invariants"
    )
    "RISK_MODEL.md" = @(
        "# Safe Change Planning Risk Model",
        "## Risk levels",
        "## Risk factors"
    )
    "PLANNING_ALGORITHM.md" = @(
        "# Safe Change Planning Algorithm",
        "## Inputs",
        "## Planning sequence"
    )
    "API_CONTRACT.md" = @(
        "# Safe Change Planning API Contract",
        "## Commands",
        "## Inputs and outputs"
    )
    "TEST_PLAN.md" = @(
        "# Safe Change Planning Test Plan",
        "## Test layers",
        "## Safety tests"
    )
    "ACCEPTANCE_CRITERIA.md" = @(
        "# Safe Change Planning Acceptance Criteria",
        "## Required evidence",
        "## Release gate"
    )
}

foreach ($Entry in $RequiredHeadings.GetEnumerator()) {
    $Path = Join-Path "docs\safe_change_planning" $Entry.Key
    $Content = Get-Content $Path -Raw

    foreach ($Heading in $Entry.Value) {
        if ($Content -notmatch [regex]::Escape($Heading)) {
            throw "Missing heading '$Heading' in $Path."
        }
    }
}

Write-Host "M3.2 architecture package is complete." -ForegroundColor Green
