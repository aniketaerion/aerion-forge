[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

function Assert-CommandSuccess {
    param([Parameter(Mandatory)][string]$Name)

    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

python -m ruff check .
Assert-CommandSuccess "Ruff"

python -m mypy .
Assert-CommandSuccess "MyPy"

python -m pytest -p no:cacheprovider
Assert-CommandSuccess "Full test suite"

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-phase4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
Assert-CommandSuccess "Phase 4 architecture validation"

foreach ($Milestone in @(
    "m4.1",
    "m4.2",
    "m4.3",
    "m4.4",
    "m4.5",
    "m4.6",
    "m4.7",
    "m4.8"
)) {
    $Validator = ".\scripts\validate-$Milestone-completion.ps1"

    if (-not (Test-Path $Validator)) {
        throw "Missing validator: $Validator"
    }

    powershell.exe `
        -NoLogo `
        -NoProfile `
        -ExecutionPolicy Bypass `
        -File $Validator `
        -RepositoryRoot $RepositoryRoot

    Assert-CommandSuccess "$Milestone completion validation"
}

Write-Host "Phase 4 completion validation passed." -ForegroundColor Green
