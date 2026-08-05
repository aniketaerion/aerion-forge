[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

python -m ruff check .
if ($LASTEXITCODE -ne 0) {
    throw "Ruff validation failed."
}

python -m mypy .
if ($LASTEXITCODE -ne 0) {
    throw "MyPy validation failed."
}

python -m pytest -p no:cacheprovider
if ($LASTEXITCODE -ne 0) {
    throw "Pytest validation failed."
}

powershell.exe `
    -NoLogo `
    -NoProfile `
    -ExecutionPolicy Bypass `
    -File ".\scripts\validate-m3.8-architecture.ps1" `
    -RepositoryRoot $RepositoryRoot

if ($LASTEXITCODE -ne 0) {
    throw "M3.8 architecture validation failed."
}

python -c "from typer.testing import CliRunner; from forge.cli import app; result = CliRunner().invoke(app, ['agent', '--help']); raise SystemExit(result.exit_code)" | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "M3.8 CLI verification failed."
}

Write-Host "M3.8 completion validation passed." -ForegroundColor Green