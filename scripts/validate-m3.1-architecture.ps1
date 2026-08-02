$Files = @(
    "docs\execution_controller\ARCHITECTURE.md",
    "docs\execution_controller\SPECIFICATION.md",
    "docs\execution_controller\STATE_MACHINE.md",
    "docs\execution_controller\DATA_MODEL.md",
    "docs\execution_controller\API_CONTRACT.md",
    "docs\execution_controller\ERROR_MODEL.md",
    "docs\execution_controller\TEST_PLAN.md",
    "docs\execution_controller\ACCEPTANCE_CRITERIA.md"
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
    throw "M3.1 architecture package is incomplete."
}

$RequiredHeadings = @{
    "ARCHITECTURE.md" = @(
        "# Execution Controller Architecture",
        "## Safety boundary",
        "## Components"
    )
    "SPECIFICATION.md" = @(
        "# Execution Controller Specification",
        "## Scope",
        "## Functional requirements"
    )
    "STATE_MACHINE.md" = @(
        "# Execution Controller State Machine",
        "## States",
        "## Transitions"
    )
    "DATA_MODEL.md" = @(
        "# Execution Controller Data Model",
        "## Entities",
        "## Invariants"
    )
    "API_CONTRACT.md" = @(
        "# Execution Controller API Contract",
        "## Commands",
        "## Inputs and outputs"
    )
    "ERROR_MODEL.md" = @(
        "# Execution Controller Error Model",
        "## Error categories",
        "## Failure behaviour"
    )
    "TEST_PLAN.md" = @(
        "# Execution Controller Test Plan",
        "## Test layers",
        "## Safety tests"
    )
    "ACCEPTANCE_CRITERIA.md" = @(
        "# Execution Controller Acceptance Criteria",
        "## Required evidence",
        "## Release gate"
    )
}

foreach ($Entry in $RequiredHeadings.GetEnumerator()) {
    $Path = Join-Path "docs\execution_controller" $Entry.Key
    $Content = Get-Content $Path -Raw

    foreach ($Heading in $Entry.Value) {
        if ($Content -notmatch [regex]::Escape($Heading)) {
            throw "Missing heading '$Heading' in $Path."
        }
    }
}

Write-Host "M3.1 architecture package is complete." -ForegroundColor Green
