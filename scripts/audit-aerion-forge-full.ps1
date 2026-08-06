[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Continue"
Set-Location $RepositoryRoot

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$AuditRoot = Join-Path $RepositoryRoot "reports\full-audit\$Timestamp"
$LogRoot = Join-Path $AuditRoot "logs"
$SummaryPath = Join-Path $AuditRoot "FULL_CODE_AUDIT_SUMMARY.md"
$JsonPath = Join-Path $AuditRoot "FULL_CODE_AUDIT.json"

New-Item -ItemType Directory -Path $LogRoot -Force | Out-Null

$Results = [System.Collections.Generic.List[object]]::new()

function Invoke-AuditStep {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Command
    )

    $SafeName = $Name -replace '[^A-Za-z0-9._-]', '_'
    $StepLog = Join-Path $LogRoot "$SafeName.log"
    $Started = Get-Date

    Write-Host ""
    Write-Host "RUNNING: $Name" -ForegroundColor Cyan

    $global:LASTEXITCODE = 0
    $Output = & $Command 2>&1
    $ExitCode = if ($null -eq $LASTEXITCODE) { 0 } else { $LASTEXITCODE }

    $Output | Tee-Object -FilePath $StepLog

    $Status = if ($ExitCode -eq 0) { "PASS" } else { "FAIL" }

    $Results.Add([pscustomobject]@{
        Name = $Name
        Status = $Status
        ExitCode = $ExitCode
        DurationSeconds = [math]::Round(((Get-Date) - $Started).TotalSeconds, 2)
        Log = $StepLog
    })

    $Color = if ($Status -eq "PASS") { "Green" } else { "Red" }
    Write-Host "$Status`: $Name" -ForegroundColor $Color
}

Invoke-AuditStep "Git status" {
    git branch --show-current
    git status --short
    git log --oneline --decorate -15
    git tag --list "forge-v*" --sort=version:refname
}

Invoke-AuditStep "Repository inventory" {
    Write-Output "Production Python files: $((Get-ChildItem .\forge -Recurse -File -Filter '*.py').Count)"
    Write-Output "Test files: $((Get-ChildItem .\tests -Recurse -File -Filter 'test_*.py').Count)"
    Write-Output "Documentation files: $((Get-ChildItem .\docs -Recurse -File -ErrorAction SilentlyContinue).Count)"
    Write-Output "Implementation scripts: $((Get-ChildItem .\scripts -File -Filter 'implement-*.ps1').Count)"
    Write-Output "Validation scripts: $((Get-ChildItem .\scripts -File -Filter 'validate-*.ps1').Count)"
}

Invoke-AuditStep "Ruff" {
    python -m ruff check .\forge .\tests
}

Invoke-AuditStep "MyPy" {
    python -m mypy .
}

Invoke-AuditStep "Pytest collection" {
    python -m pytest --collect-only -q -p no:cacheprovider
}

Invoke-AuditStep "Full test suite" {
    python -m pytest -p no:cacheprovider
}

Invoke-AuditStep "Placeholder scan" {
    $Patterns = @(
        "NotImplementedError",
        "raise NotImplemented",
        "TODO",
        "FIXME",
        "HACK",
        "XXX"
    )

    $Matches = Get-ChildItem .\forge -Recurse -File -Filter "*.py" |
        Select-String -Pattern $Patterns -SimpleMatch

    if ($Matches) {
        $Matches |
            Select-Object Path, LineNumber, Line |
            Format-Table -AutoSize |
            Out-String |
            Write-Output
        $global:LASTEXITCODE = 1
    }
    else {
        Write-Output "No unfinished-code markers detected."
        $global:LASTEXITCODE = 0
    }
}

if (Get-Command forge -ErrorAction SilentlyContinue) {
    Invoke-AuditStep "Forge native audit" {
        forge audit
    }
}
elseif (Test-Path ".\scripts\audit-aerion-forge-progress.ps1") {
    Invoke-AuditStep "Forge progress audit" {
        powershell.exe `
            -NoLogo `
            -NoProfile `
            -ExecutionPolicy Bypass `
            -File ".\scripts\audit-aerion-forge-progress.ps1"
    }
}

$ValidationScripts = Get-ChildItem ".\scripts" -File -Filter "validate-*.ps1" |
    Where-Object { $_.Length -gt 0 } |
    Sort-Object Name

foreach ($Script in $ValidationScripts) {
    $ScriptPath = $Script.FullName
    $ScriptName = $Script.BaseName

    Invoke-AuditStep $ScriptName {
        powershell.exe `
            -NoLogo `
            -NoProfile `
            -ExecutionPolicy Bypass `
            -File $ScriptPath `
            -RepositoryRoot $RepositoryRoot
    }
}

$Branch = (git branch --show-current).Trim()
$Commit = (git rev-parse --short HEAD).Trim()
$CommitMessage = (git log -1 --pretty=%s).Trim()
$WorkingTree = @(git status --short)
$Failed = @($Results | Where-Object Status -eq "FAIL")
$OverallStatus = if ($Failed.Count -eq 0) { "PASS" } else { "FAIL" }

$AuditObject = [ordered]@{
    GeneratedAt = (Get-Date).ToString("o")
    OverallStatus = $OverallStatus
    Branch = $Branch
    Commit = $Commit
    CommitMessage = $CommitMessage
    WorkingTree = $WorkingTree
    Results = $Results
}

$AuditObject |
    ConvertTo-Json -Depth 8 |
    Out-File -FilePath $JsonPath -Encoding utf8

$Markdown = [System.Collections.Generic.List[string]]::new()
$Markdown.Add("# Aerion Forge Full Code Audit")
$Markdown.Add("")
$Markdown.Add("Generated: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')")
$Markdown.Add("")
$Markdown.Add("## Executive Result")
$Markdown.Add("")
$Markdown.Add("| Field | Result |")
$Markdown.Add("|---|---|")
$Markdown.Add("| Overall status | **$OverallStatus** |")
$Markdown.Add("| Branch | $Branch |")
$Markdown.Add("| Commit | $Commit |")
$Markdown.Add("| Commit message | $CommitMessage |")
$Markdown.Add("| Working-tree entries | $($WorkingTree.Count) |")
$Markdown.Add("")
$Markdown.Add("## Audit Results")
$Markdown.Add("")
$Markdown.Add("| Check | Status | Exit code | Duration |")
$Markdown.Add("|---|---|---:|---:|")

foreach ($Result in $Results) {
    $Markdown.Add(
        "| $($Result.Name) | $($Result.Status) | " +
        "$($Result.ExitCode) | $($Result.DurationSeconds) sec |"
    )
}

$Markdown.Add("")
$Markdown.Add("## Working Tree")
$Markdown.Add("")
$Markdown.Add('```text')

if ($WorkingTree.Count -eq 0) {
    $Markdown.Add("Clean")
}
else {
    foreach ($Line in $WorkingTree) {
        $Markdown.Add($Line)
    }
}

$Markdown.Add('```')
$Markdown.Add("")
$Markdown.Add("## Detailed Logs")
$Markdown.Add("")
$Markdown.Add($LogRoot)

$Markdown |
    Out-File -FilePath $SummaryPath -Encoding utf8

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "FULL AERION FORGE AUDIT COMPLETE" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Status:  $OverallStatus"
Write-Host "Summary: $SummaryPath"
Write-Host "JSON:    $JsonPath"
Write-Host "Logs:    $LogRoot"
Write-Host ""

$Results | Format-Table -AutoSize
Get-Item $SummaryPath, $JsonPath |
    Select-Object FullName, Length, LastWriteTime
