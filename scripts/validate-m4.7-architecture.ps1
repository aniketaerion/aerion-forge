[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Stop"
Set-Location $RepositoryRoot

$RequiredFiles = @(
    "forge\domain_intelligence\knowledge_loader\__init__.py",
    "forge\domain_intelligence\knowledge_loader\cache.py",
    "forge\domain_intelligence\knowledge_loader\chunking.py",
    "forge\domain_intelligence\knowledge_loader\cli.py",
    "forge\domain_intelligence\knowledge_loader\compatibility.py",
    "forge\domain_intelligence\knowledge_loader\discovery.py",
    "forge\domain_intelligence\knowledge_loader\errors.py",
    "forge\domain_intelligence\knowledge_loader\identifiers.py",
    "forge\domain_intelligence\knowledge_loader\loader.py",
    "forge\domain_intelligence\knowledge_loader\manifest.py",
    "forge\domain_intelligence\knowledge_loader\models.py",
    "forge\domain_intelligence\knowledge_loader\policies.py",
    "forge\domain_intelligence\knowledge_loader\registry.py",
    "forge\domain_intelligence\knowledge_loader\reporting.py",
    "forge\domain_intelligence\knowledge_loader\resolver.py",
    "forge\domain_intelligence\knowledge_loader\service.py",
    "forge\domain_intelligence\knowledge_loader\validation.py",
    "forge\domain_intelligence\knowledge_loader\versioning.py",
    "docs\domain_intelligence\knowledge_loader\ARCHITECTURE.md",
    "docs\domain_intelligence\knowledge_loader\SPECIFICATION.md",
    "docs\domain_intelligence\knowledge_loader\DATA_MODEL.md",
    "docs\domain_intelligence\knowledge_loader\SECURITY_MODEL.md",
    "docs\domain_intelligence\knowledge_loader\ACCEPTANCE_CRITERIA.md"
)

$Missing = @(
    $RequiredFiles |
        Where-Object { -not (Test-Path $_) }
)

if ($Missing.Count -gt 0) {
    $Missing | ForEach-Object {
        Write-Host "MISSING: $_" -ForegroundColor Red
    }

    throw "M4.7 architecture validation failed."
}

$CliContent = Get-Content ".\forge\cli.py" -Raw

if ($CliContent -notmatch 'knowledge_loader_app') {
    throw "M4.7 knowledge-loader CLI is not registered."
}

if ($CliContent -notmatch 'name="knowledge-loader"') {
    throw "M4.7 knowledge-loader command is not registered."
}

$ServiceContent = Get-Content `
    ".\forge\domain_intelligence\knowledge_loader\service.py" `
    -Raw

foreach ($RequiredSymbol in @(
    "discover_knowledge_sources",
    "chunk_documents",
    "analyze_knowledge_compatibility",
    "validate_documents",
    "validate_chunks",
    "KnowledgeLoaderRegistry"
)) {
    if ($ServiceContent -notmatch [regex]::Escape($RequiredSymbol)) {
        throw "M4.7 service is missing $RequiredSymbol."
    }
}

Write-Host "M4.7 architecture validation passed." -ForegroundColor Green