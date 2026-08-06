[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredDocs = @(
    ".\docs\autonomous_runtime\ARCHITECTURE.md",
    ".\docs\autonomous_runtime\SPECIFICATION.md",
    ".\docs\autonomous_runtime\DATA_MODEL.md",
    ".\docs\autonomous_runtime\STATE_MACHINE.md",
    ".\docs\autonomous_runtime\AUTHORITY_MODEL.md",
    ".\docs\autonomous_runtime\EVENT_MODEL.md",
    ".\docs\autonomous_runtime\RECOVERY_MODEL.md",
    ".\docs\autonomous_runtime\ACCEPTANCE_CRITERIA.md",
    ".\docs\autonomous_runtime\DECISIONS.md"
)

$RequiredModules = @(
    ".\forge\autonomous_runtime\states.py",
    ".\forge\autonomous_runtime\models.py",
    ".\forge\autonomous_runtime\transitions.py",
    ".\forge\autonomous_runtime\authority.py",
    ".\forge\autonomous_runtime\approvals.py",
    ".\forge\autonomous_runtime\checkpoints.py",
    ".\forge\autonomous_runtime\recovery.py",
    ".\forge\autonomous_runtime\events.py",
    ".\forge\autonomous_runtime\reporting.py",
    ".\forge\autonomous_runtime\cli.py"
)

foreach ($Path in @($RequiredDocs + $RequiredModules)) {
    if (-not (Test-Path $Path)) {
        throw "Required M5.1 architecture artifact is missing: $Path"
    }

    if ((Get-Item $Path).Length -eq 0) {
        throw "Required M5.1 architecture artifact is empty: $Path"
    }
}

$Placeholders = Get-ChildItem `
    ".\docs\autonomous_runtime" `
    -File |
    Select-String -Pattern "_To be completed\._"

if ($Placeholders) {
    throw "M5.1 architecture documents contain placeholders."
}

Write-Host "M5.1 architecture validation passed." -ForegroundColor Green