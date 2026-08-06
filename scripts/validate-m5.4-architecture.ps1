[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_decision\ARCHITECTURE.md",
    ".\docs\autonomous_decision\SPECIFICATION.md",
    ".\docs\autonomous_decision\DATA_MODEL.md",
    ".\docs\autonomous_decision\DECISION_MODEL.md",
    ".\docs\autonomous_decision\CANDIDATE_MODEL.md",
    ".\docs\autonomous_decision\CONFIDENCE_MODEL.md",
    ".\docs\autonomous_decision\POLICY_MODEL.md",
    ".\docs\autonomous_decision\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_decision\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_decision\models.py",
    ".\forge\autonomous_decision\policies.py",
    ".\forge\autonomous_decision\candidate_generator.py",
    ".\forge\autonomous_decision\candidate_service.py",
    ".\forge\autonomous_decision\assessment_service.py",
    ".\forge\autonomous_decision\ranking.py",
    ".\forge\autonomous_decision\selector.py",
    ".\forge\autonomous_decision\decision_service.py",
    ".\forge\autonomous_decision\reporting.py",
    ".\forge\autonomous_decision\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.4 artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.4 artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_decision" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.4 architecture documents contain placeholders."
}

$Architecture = Get-Content `
    ".\docs\autonomous_decision\ARCHITECTURE.md" `
    -Raw

foreach ($RequiredPhrase in @(
    "No tool execution inside M5.4",
    "Candidate generation is bounded",
    "Every selected action has supporting evidence",
    "Decision records are immutable"
)) {
    if (-not $Architecture.Contains($RequiredPhrase)) {
        throw "M5.4 architecture principle missing: $RequiredPhrase"
    }
}

Write-Host "M5.4 architecture validation passed." `
    -ForegroundColor Green