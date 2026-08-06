[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_memory\ARCHITECTURE.md",
    ".\docs\autonomous_memory\SPECIFICATION.md",
    ".\docs\autonomous_memory\DATA_MODEL.md",
    ".\docs\autonomous_memory\MEMORY_MODEL.md",
    ".\docs\autonomous_memory\RETRIEVAL_MODEL.md",
    ".\docs\autonomous_memory\LEARNING_MODEL.md",
    ".\docs\autonomous_memory\RETENTION_MODEL.md",
    ".\docs\autonomous_memory\POLICY_MODEL.md",
    ".\docs\autonomous_memory\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_memory\DECISIONS.md"
)

foreach ($Path in $RequiredDocs) {
    if (-not (Test-Path $Path)) {
        throw "Missing architecture document: $Path"
    }

    if ((Get-Item $Path).Length -lt 300) {
        throw "Architecture document too small: $Path"
    }
}

$RequiredModules = @(
    ".\forge\autonomous_memory\models.py",
    ".\forge\autonomous_memory\policies.py",
    ".\forge\autonomous_memory\ingestion.py",
    ".\forge\autonomous_memory\storage.py",
    ".\forge\autonomous_memory\retrieval.py",
    ".\forge\autonomous_memory\learning.py",
    ".\forge\autonomous_memory\reporting.py",
    ".\forge\autonomous_memory\cli.py"
)

foreach ($Path in $RequiredModules) {
    if (-not (Test-Path $Path)) {
        throw "Missing implementation module: $Path"
    }
}

Write-Host "M5.5 architecture validation passed." `
    -ForegroundColor Green