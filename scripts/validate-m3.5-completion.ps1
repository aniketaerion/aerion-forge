[CmdletBinding()]
param([string]$RepositoryRoot = (Resolve-Path ".").Path)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

python -m ruff check .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m mypy .
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File `
    ".\scripts\validate-m3.5-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Help = forge autonomous-repair --help 2>&1 | Out-String
if (
    $LASTEXITCODE -ne 0 -or
    $Help -notmatch "providers" -or
    $Help -notmatch "propose" -or
    $Help -notmatch "dry-run" -or
    $Help -notmatch "apply"
) {
    throw "forge autonomous-repair CLI is not registered correctly"
}

$Providers = forge autonomous-repair providers 2>&1 | Out-String
if (
    $LASTEXITCODE -ne 0 -or
    $Providers -notmatch "exact_patch" -or
    $Providers -notmatch "ruff_fix"
) {
    throw "built-in autonomous repair providers are unavailable"
}

Write-Host "M3.5 completion validation passed." -ForegroundColor Green