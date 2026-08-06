[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\embedded\__init__.py",
    "forge\domain_intelligence\embedded\ardupilot.py",
    "forge\domain_intelligence\embedded\build_systems.py",
    "forge\domain_intelligence\embedded\cli.py",
    "forge\domain_intelligence\embedded\errors.py",
    "forge\domain_intelligence\embedded\identifiers.py",
    "forge\domain_intelligence\embedded\interfaces.py",
    "forge\domain_intelligence\embedded\messages.py",
    "forge\domain_intelligence\embedded\models.py",
    "forge\domain_intelligence\embedded\policies.py",
    "forge\domain_intelligence\embedded\px4.py",
    "forge\domain_intelligence\embedded\registry.py",
    "forge\domain_intelligence\embedded\reporting.py",
    "forge\domain_intelligence\embedded\ros2.py",
    "forge\domain_intelligence\embedded\safety.py",
    "forge\domain_intelligence\embedded\service.py",
    "forge\domain_intelligence\embedded\stm32.py",
    "docs\domain_intelligence\embedded\ARCHITECTURE.md",
    "docs\domain_intelligence\embedded\SPECIFICATION.md",
    "docs\domain_intelligence\embedded\DATA_MODEL.md",
    "docs\domain_intelligence\embedded\SECURITY_MODEL.md",
    "docs\domain_intelligence\embedded\ACCEPTANCE_CRITERIA.md"
)

$Missing = @(
    $RequiredFiles |
        Where-Object { -not (Test-Path $_) }
)

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "M4.6 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'embedded_app') {
    throw "M4.6 embedded CLI is not registered in forge/cli.py."
}

if ($CliContent -notmatch 'name="embedded"') {
    throw "M4.6 embedded command is not registered."
}

$ServiceContent = Get-Content `
    ".\forge\domain_intelligence\embedded\service.py" `
    -Raw

foreach ($RequiredSymbol in @(
    "discover_embedded_build_files",
    "discover_embedded_interfaces",
    "discover_embedded_messages",
    "analyze_embedded_safety",
    "EmbeddedAnalyzerRegistry"
)) {
    if ($ServiceContent -notmatch [regex]::Escape($RequiredSymbol)) {
        throw "M4.6 service is missing $RequiredSymbol."
    }
}

Write-Host "M4.6 architecture validation passed." -ForegroundColor Green