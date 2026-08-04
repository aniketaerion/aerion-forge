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
    ".\scripts\validate-m3.4-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

$Help = forge repair --help 2>&1 | Out-String
if ($LASTEXITCODE -ne 0 -or $Help -notmatch "validate" -or $Help -notmatch "plan") {
    throw "forge repair CLI is not registered correctly"
}

Write-Host "M3.4 completion validation passed." -ForegroundColor Green