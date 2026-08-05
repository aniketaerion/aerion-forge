[CmdletBinding()]
param(
    [string]$RepositoryRoot = "D:\Software Dev\Aerion Forge"
)

$ErrorActionPreference = "Continue"
$ProgressPreference = "SilentlyContinue"

$RepositoryRoot = (Resolve-Path $RepositoryRoot).Path
Set-Location $RepositoryRoot

$AuditDir = Join-Path $RepositoryRoot "audit"
New-Item -ItemType Directory -Path $AuditDir -Force | Out-Null

$ReportMd       = Join-Path $AuditDir "AERION_FORGE_PROGRESS_AUDIT.md"
$ReportJson     = Join-Path $AuditDir "AERION_FORGE_PROGRESS_AUDIT.json"
$FileCsv        = Join-Path $AuditDir "AERION_FORGE_FILE_INVENTORY.csv"
$TestCsv        = Join-Path $AuditDir "AERION_FORGE_TEST_INVENTORY.csv"
$GitFile        = Join-Path $AuditDir "AERION_FORGE_GIT_EVIDENCE.txt"
$CapabilityFile = Join-Path $AuditDir "AERION_FORGE_CAPABILITY_REGISTRY.json"
$ValidationFile = Join-Path $AuditDir "AERION_FORGE_VALIDATION_RESULTS.txt"
$RiskFile       = Join-Path $AuditDir "AERION_FORGE_INCONSISTENCIES.md"

function Invoke-Captured {
    param(
        [Parameter(Mandatory)][string]$Name,
        [Parameter(Mandatory)][scriptblock]$Command
    )

    $sw = [Diagnostics.Stopwatch]::StartNew()
    $output = @()
    $exitCode = 0

    try {
        $global:LASTEXITCODE = 0
        $output = & $Command 2>&1 | ForEach-Object { $_.ToString() }
        if ($null -ne $LASTEXITCODE) {
            $exitCode = [int]$LASTEXITCODE
        }
    }
    catch {
        $exitCode = 1
        $output += $_.Exception.ToString()
    }
    finally {
        $sw.Stop()
    }

    [pscustomobject]@{
        Name = $Name
        Status = if ($exitCode -eq 0) { "PASS" } else { "FAIL" }
        ExitCode = $exitCode
        DurationSeconds = [math]::Round($sw.Elapsed.TotalSeconds, 2)
        Output = @($output)
    }
}

function Get-RelativePath {
    param([string]$Path)
    try {
        return [IO.Path]::GetRelativePath($RepositoryRoot, $Path)
    }
    catch {
        return $Path.Replace($RepositoryRoot, "").TrimStart("\", "/")
    }
}

function Get-Milestone {
    param([string]$Text)
    $m = [regex]::Match($Text, '(?i)(?:^|[^a-z0-9])m([0-5])[\.\-_ ]?([0-9]+)(?:[^0-9]|$)')
    if ($m.Success) {
        return "M$($m.Groups[1].Value).$($m.Groups[2].Value)"
    }
    return ""
}

function Get-Phase {
    param([string]$Text)
    $lower = $Text.ToLowerInvariant()

    if ($lower -match 'phase.?5|autonomous|orchestrat') { return "Phase 5" }
    if ($lower -match 'phase.?4|erp') { return "Phase 4" }
    if ($lower -match 'phase.?3|execution|safe.change|safe.code|editing|rollback|build.verification') { return "Phase 3" }
    if ($lower -match 'phase.?2|mission|task|impact|memory|planning') { return "Phase 2" }
    if ($lower -match 'phase.?1|workspace|discover|index|graph|capabilit|config|health|diagnos') { return "Phase 1" }
    if ($lower -match 'phase.?0|foundation|pyproject|readme|gitignore') { return "Phase 0" }

    $milestone = Get-Milestone $Text
    if ($milestone) {
        return "Phase $($milestone.Substring(1,1))"
    }

    return "Unconfirmed"
}

$Started = Get-Date
$Findings = [System.Collections.Generic.List[object]]::new()

Write-Host "[AUDIT] Aerion Forge audit started" -ForegroundColor Cyan
Write-Host "[AUDIT] Repository: $RepositoryRoot" -ForegroundColor Cyan

# ---------------------------------------------------------------------------
# Git evidence
# ---------------------------------------------------------------------------

Write-Host "[1/8] Git evidence" -ForegroundColor Cyan

$Git = [ordered]@{
    CurrentBranch = Invoke-Captured "Current branch" { git branch --show-current }
    WorkingTree   = Invoke-Captured "Working tree" { git status --short }
    Head          = Invoke-Captured "HEAD" { git rev-parse HEAD }
    Main          = Invoke-Captured "main" { git rev-parse main }
    OriginMain    = Invoke-Captured "origin/main" { git rev-parse origin/main }
    Tags          = Invoke-Captured "Forge tags" { git tag --list "forge-v*" --sort=version:refname }
    TagMap        = Invoke-Captured "Tag mapping" {
        git for-each-ref refs/tags/forge-v* --format="%(refname:short)|%(objectname)|%(creatordate:iso8601)|%(subject)"
    }
    LocalBranches = Invoke-Captured "Local branches" { git branch --format="%(refname:short)|%(objectname)|%(upstream:short)" }
    RemoteBranches= Invoke-Captured "Remote branches" { git branch -r --format="%(refname:short)|%(objectname)" }
    RecentCommits = Invoke-Captured "Recent commits" {
        git log -100 --date=iso-strict --pretty=format:"%H|%ad|%an|%s"
    }
    MergeBase     = Invoke-Captured "main/origin-main merge base" { git merge-base main origin/main }
}

$GitLines = @("AERION FORGE GIT EVIDENCE","Generated: $(Get-Date -Format o)","")
foreach ($entry in $Git.GetEnumerator()) {
    $GitLines += "=" * 80
    $GitLines += $entry.Key
    $GitLines += "Status: $($entry.Value.Status)"
    $GitLines += "Exit code: $($entry.Value.ExitCode)"
    $GitLines += "Duration: $($entry.Value.DurationSeconds)s"
    $GitLines += "-" * 80
    $GitLines += $entry.Value.Output
    $GitLines += ""
}
$GitLines | Set-Content $GitFile -Encoding utf8

$CurrentBranch = $Git.CurrentBranch.Output | Select-Object -First 1
$HeadCommit = $Git.Head.Output | Select-Object -First 1
$MainCommit = $Git.Main.Output | Select-Object -First 1
$OriginMainCommit = $Git.OriginMain.Output | Select-Object -First 1
$WorkingTreeClean = ($Git.WorkingTree.Output.Count -eq 0)

if (-not $WorkingTreeClean) {
    $Findings.Add([pscustomobject]@{
        Severity = "MEDIUM"
        Area = "Git"
        Issue = "Working tree is not clean."
        Evidence = ($Git.WorkingTree.Output -join "; ")
    })
}

if ($MainCommit -and $OriginMainCommit -and $MainCommit -ne $OriginMainCommit) {
    $Findings.Add([pscustomobject]@{
        Severity = "HIGH"
        Area = "Git"
        Issue = "Local main differs from origin/main."
        Evidence = "main=$MainCommit; origin/main=$OriginMainCommit"
    })
}

# ---------------------------------------------------------------------------
# File inventory
# ---------------------------------------------------------------------------

Write-Host "[2/8] Repository file inventory" -ForegroundColor Cyan

$Inventory = @()
foreach ($RootName in @("forge", "tests", "docs", "scripts")) {
    $RootPath = Join-Path $RepositoryRoot $RootName

    if (-not (Test-Path $RootPath)) {
        $Findings.Add([pscustomobject]@{
            Severity = "HIGH"
            Area = "Repository"
            Issue = "Expected repository area is missing."
            Evidence = $RootPath
        })
        continue
    }

    $Inventory += Get-ChildItem $RootPath -File -Recurse -Force |
        Where-Object {
            $_.FullName -notmatch '[\\/]\.git[\\/]' -and
            $_.FullName -notmatch '[\\/]\.venv[\\/]' -and
            $_.FullName -notmatch '[\\/]venv[\\/]' -and
            $_.FullName -notmatch '[\\/]__pycache__[\\/]'
        } |
        ForEach-Object {
            $Relative = Get-RelativePath $_.FullName
            $Classification = if ($Relative -match '^forge[\\/]') {
                "production"
            }
            elseif ($Relative -match '^tests[\\/]') {
                "test"
            }
            elseif ($Relative -match '^docs[\\/]') {
                "documentation"
            }
            elseif ($Relative -match '^scripts[\\/]validate-.*\.ps1$') {
                "validation"
            }
            else {
                "script"
            }

            [pscustomobject]@{
                RelativePath = $Relative
                Classification = $Classification
                Extension = $_.Extension
                SizeBytes = $_.Length
                NonEmpty = ($_.Length -gt 0)
                LastModifiedUtc = $_.LastWriteTimeUtc.ToString("o")
                ProbablePhase = Get-Phase $Relative
                ProbableMilestone = Get-Milestone $Relative
            }
        }
}

foreach ($RootFile in @("pyproject.toml", "README.md", ".gitignore")) {
    $Path = Join-Path $RepositoryRoot $RootFile
    if (Test-Path $Path) {
        $Item = Get-Item $Path
        $Inventory += [pscustomobject]@{
            RelativePath = $RootFile
            Classification = "foundation"
            Extension = $Item.Extension
            SizeBytes = $Item.Length
            NonEmpty = ($Item.Length -gt 0)
            LastModifiedUtc = $Item.LastWriteTimeUtc.ToString("o")
            ProbablePhase = "Phase 0"
            ProbableMilestone = ""
        }
    }
}

$Inventory | Sort-Object RelativePath |
    Export-Csv $FileCsv -NoTypeInformation -Encoding utf8

$EmptyFiles = @($Inventory | Where-Object { -not $_.NonEmpty })
foreach ($File in $EmptyFiles) {
    $Findings.Add([pscustomobject]@{
        Severity = "MEDIUM"
        Area = "Files"
        Issue = "Empty file detected."
        Evidence = $File.RelativePath
    })
}

# ---------------------------------------------------------------------------
# Test inventory
# ---------------------------------------------------------------------------

Write-Host "[3/8] Test inventory" -ForegroundColor Cyan

$TestInventory = foreach ($File in $Inventory | Where-Object {
    $_.Classification -eq "test" -and $_.Extension -eq ".py"
}) {
    $Path = Join-Path $RepositoryRoot $File.RelativePath
    $Text = ""
    try { $Text = Get-Content $Path -Raw } catch {}

    [pscustomobject]@{
        RelativePath = $File.RelativePath
        ProbablePhase = $File.ProbablePhase
        ProbableMilestone = $File.ProbableMilestone
        TestFunctions = ([regex]::Matches(
            $Text,
            '(?m)^\s*(?:async\s+)?def\s+test_[A-Za-z0-9_]+\s*\('
        )).Count
        TestClasses = ([regex]::Matches(
            $Text,
            '(?m)^\s*class\s+Test[A-Za-z0-9_]*'
        )).Count
        SizeBytes = $File.SizeBytes
    }
}

$TestInventory | Sort-Object RelativePath |
    Export-Csv $TestCsv -NoTypeInformation -Encoding utf8

# ---------------------------------------------------------------------------
# Placeholder scan
# ---------------------------------------------------------------------------

Write-Host "[4/8] Source placeholder scan" -ForegroundColor Cyan

$Markers = @()
foreach ($File in $Inventory | Where-Object {
    $_.Classification -eq "production" -and $_.Extension -eq ".py"
}) {
    $Path = Join-Path $RepositoryRoot $File.RelativePath
    $LineNumber = 0

    Get-Content $Path -ErrorAction SilentlyContinue | ForEach-Object {
        $LineNumber++
        if ($_ -match '(?i)\bTODO\b|\bFIXME\b|NotImplementedError|\bplaceholder\b') {
            $Markers += [pscustomobject]@{
                File = $File.RelativePath
                Line = $LineNumber
                Text = $_.Trim()
            }
        }
    }
}

foreach ($Marker in $Markers) {
    $Findings.Add([pscustomobject]@{
        Severity = if ($Marker.Text -match 'NotImplementedError') { "HIGH" } else { "LOW" }
        Area = "Source"
        Issue = "Potential incomplete implementation marker."
        Evidence = "$($Marker.File):$($Marker.Line) - $($Marker.Text)"
    })
}

# ---------------------------------------------------------------------------
# Static checks and tests
# ---------------------------------------------------------------------------

Write-Host "[5/8] Ruff, MyPy and pytest" -ForegroundColor Cyan

$Ruff = Invoke-Captured "Ruff" { python -m ruff check . }
$MyPy = Invoke-Captured "MyPy" { python -m mypy . }
$Pytest = Invoke-Captured "Pytest" { python -m pytest -p no:cacheprovider }

@("RUFF","Exit code: $($Ruff.ExitCode)","",$Ruff.Output) |
    Set-Content (Join-Path $AuditDir "AERION_FORGE_RUFF_RESULTS.txt") -Encoding utf8

@("MYPY","Exit code: $($MyPy.ExitCode)","",$MyPy.Output) |
    Set-Content (Join-Path $AuditDir "AERION_FORGE_MYPY_RESULTS.txt") -Encoding utf8

@("PYTEST","Exit code: $($Pytest.ExitCode)","",$Pytest.Output) |
    Set-Content (Join-Path $AuditDir "AERION_FORGE_PYTEST_RESULTS.txt") -Encoding utf8

if ($Ruff.ExitCode -ne 0) {
    $Findings.Add([pscustomobject]@{
        Severity = "HIGH"
        Area = "Quality"
        Issue = "Ruff failed."
        Evidence = ($Ruff.Output | Select-Object -First 20) -join "; "
    })
}

if ($MyPy.ExitCode -ne 0) {
    $Findings.Add([pscustomobject]@{
        Severity = "HIGH"
        Area = "Quality"
        Issue = "MyPy failed."
        Evidence = ($MyPy.Output | Select-Object -First 20) -join "; "
    })
}

if ($Pytest.ExitCode -ne 0) {
    $Findings.Add([pscustomobject]@{
        Severity = "CRITICAL"
        Area = "Tests"
        Issue = "pytest failed."
        Evidence = ($Pytest.Output | Select-Object -Last 20) -join "; "
    })
}

$PytestText = $Pytest.Output -join "`n"
function Get-PytestCount {
    param([string]$Word)
    $M = [regex]::Match($PytestText, "(?i)(\d+)\s+$Word")
    if ($M.Success) { return [int]$M.Groups[1].Value }
    return 0
}

$CollectedMatch = [regex]::Match($PytestText, '(?i)collected\s+(\d+)\s+items?')
$Passed = Get-PytestCount "passed"
$Failed = Get-PytestCount "failed"
$Skipped = Get-PytestCount "skipped"
$XFailed = Get-PytestCount "xfailed"
$XPassed = Get-PytestCount "xpassed"

$Collected = if ($CollectedMatch.Success) {
    [int]$CollectedMatch.Groups[1].Value
}
else {
    $Passed + $Failed + $Skipped + $XFailed + $XPassed
}

# ---------------------------------------------------------------------------
# Validation scripts
# ---------------------------------------------------------------------------

Write-Host "[6/8] Milestone validation scripts" -ForegroundColor Cyan

$ValidationResults = @()
$ValidationText = @(
    "AERION FORGE VALIDATION RESULTS",
    "Generated: $(Get-Date -Format o)",
    ""
)

$ValidationScripts = @(
    Get-ChildItem (Join-Path $RepositoryRoot "scripts") `
        -Filter "validate-*.ps1" `
        -File `
        -ErrorAction SilentlyContinue |
        Sort-Object Name
)

foreach ($Script in $ValidationScripts) {
    Write-Host "  Running $($Script.Name)" -ForegroundColor DarkCyan
    $FullPath = $Script.FullName

    $Result = Invoke-Captured $Script.Name {
        & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $FullPath
    }

    $ValidationResults += [pscustomobject]@{
        Script = Get-RelativePath $Script.FullName
        Milestone = Get-Milestone $Script.Name
        Status = $Result.Status
        ExitCode = $Result.ExitCode
        DurationSeconds = $Result.DurationSeconds
        Output = $Result.Output
    }

    $ValidationText += "=" * 80
    $ValidationText += "Script: $(Get-RelativePath $Script.FullName)"
    $ValidationText += "Milestone: $(Get-Milestone $Script.Name)"
    $ValidationText += "Status: $($Result.Status)"
    $ValidationText += "Exit code: $($Result.ExitCode)"
    $ValidationText += "Duration: $($Result.DurationSeconds)s"
    $ValidationText += "-" * 80
    $ValidationText += $Result.Output
    $ValidationText += ""

    if ($Result.ExitCode -ne 0) {
        $Findings.Add([pscustomobject]@{
            Severity = "HIGH"
            Area = "Validation"
            Issue = "Validation script failed."
            Evidence = "$($Script.Name), exit code $($Result.ExitCode)"
        })
    }
}

$ValidationText | Set-Content $ValidationFile -Encoding utf8

# ---------------------------------------------------------------------------
# Capability registry
# ---------------------------------------------------------------------------

Write-Host "[7/8] Capability catalogue" -ForegroundColor Cyan

$CapabilityPython = @'
import dataclasses
import enum
import json
import pathlib
import traceback

root = pathlib.Path.cwd()
output = root / "audit" / "AERION_FORGE_CAPABILITY_REGISTRY.json"

def encode(value):
    if dataclasses.is_dataclass(value):
        return {f.name: encode(getattr(value, f.name)) for f in dataclasses.fields(value)}
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, pathlib.Path):
        return str(value)
    if isinstance(value, dict):
        return {str(k): encode(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [encode(v) for v in value]
    if hasattr(value, "model_dump"):
        return encode(value.model_dump())
    if hasattr(value, "__dict__"):
        public = {k: encode(v) for k, v in vars(value).items() if not k.startswith("_")}
        if public:
            return public
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)

payload = {
    "status": "NOT_FOUND",
    "count": 0,
    "capabilities": [],
    "error": None,
}

try:
    from forge.capabilities.catalogue import built_in_catalogue

    catalogue = built_in_catalogue
    if callable(catalogue):
        catalogue = catalogue()

    if isinstance(catalogue, dict):
        items = list(catalogue.values())
    elif hasattr(catalogue, "capabilities"):
        items = list(catalogue.capabilities)
    else:
        try:
            items = list(catalogue)
        except TypeError:
            items = [catalogue]

    payload["status"] = "LOADED"
    payload["capabilities"] = [encode(item) for item in items]
    payload["count"] = len(payload["capabilities"])

except Exception:
    payload["status"] = "ERROR"
    payload["error"] = traceback.format_exc()

output.write_text(
    json.dumps(payload, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print(json.dumps({
    "status": payload["status"],
    "count": payload["count"],
    "error": payload["error"],
}, ensure_ascii=False))
'@

$CapabilityResult = Invoke-Captured "Capability catalogue" {
    $CapabilityPython | python -
}

$CapabilityData = $null
if (Test-Path $CapabilityFile) {
    try {
        $CapabilityData = Get-Content $CapabilityFile -Raw | ConvertFrom-Json
    }
    catch {
        $Findings.Add([pscustomobject]@{
            Severity = "HIGH"
            Area = "Capabilities"
            Issue = "Capability JSON could not be parsed."
            Evidence = $_.Exception.Message
        })
    }
}

if (-not $CapabilityData -or $CapabilityData.status -ne "LOADED") {
    $Findings.Add([pscustomobject]@{
        Severity = "HIGH"
        Area = "Capabilities"
        Issue = "Built-in capability catalogue could not be loaded."
        Evidence = ($CapabilityResult.Output -join "; ")
    })
}

# ---------------------------------------------------------------------------
# Milestone and phase evidence
# ---------------------------------------------------------------------------

Write-Host "[8/8] Milestone, phase and programme report" -ForegroundColor Cyan

$ExpectedMilestones = @(
    "M1.1","M1.2","M1.3","M1.4","M1.5","M1.6","M1.7","M1.8",
    "M2.1","M2.2","M2.3","M2.4","M2.5","M2.6","M2.7","M2.8",
    "M3.1","M3.2","M3.3","M3.4","M3.5","M3.6","M3.7","M3.8","M3.9","M3.10",
    "M4.1","M4.2","M4.3","M4.4","M4.5","M4.6","M4.7","M4.8",
    "M5.1","M5.2","M5.3","M5.4","M5.5","M5.6","M5.7","M5.8"
)

$MilestoneMap = @{
    "M1.1" = @{
        Name = "Workspace Manager"
        ProductionRegex = '^forge[\\/]workspace[\\/]'
        TestRegex = '^tests[\\/].*workspace'
        DocumentationRegex = '^docs[\\/].*workspace'
    }
    "M1.2" = @{
        Name = "Repository Discovery"
        ProductionRegex = '^forge[\\/]discovery[\\/]'
        TestRegex = '^tests[\\/].*discovery'
        DocumentationRegex = '^docs[\\/].*discovery'
    }
    "M1.3" = @{
        Name = "Incremental Project Index"
        ProductionRegex = '^forge[\\/]indexing[\\/]'
        TestRegex = '^tests[\\/].*index'
        DocumentationRegex = '^docs[\\/].*index'
    }
    "M1.4" = @{
        Name = "Engineering Knowledge Graph"
        ProductionRegex = '^forge[\\/]knowledge[\\/]'
        TestRegex = '^tests[\\/].*(knowledge|graph)'
        DocumentationRegex = '^docs[\\/].*(knowledge|graph)'
    }
    "M1.5" = @{
        Name = "Capability Registry"
        ProductionRegex = '^forge[\\/]capabilities[\\/]'
        TestRegex = '^tests[\\/].*capabilit'
        DocumentationRegex = '^docs[\\/].*capabilit'
    }
    "M1.6" = @{
        Name = "Runtime Configuration"
        ProductionRegex = '^forge[\\/](config|configuration)[\\/]'
        TestRegex = '^tests[\\/].*(config|configuration)'
        DocumentationRegex = '^docs[\\/].*(config|configuration)'
    }
    "M1.7" = @{
        Name = "Runtime Health and Diagnostics"
        ProductionRegex = '^forge[\\/]diagnostics[\\/]'
        TestRegex = '^tests[\\/].*diagnostic'
        DocumentationRegex = '^docs[\\/].*diagnostic'
    }
    "M1.8" = @{
        Name = "Validation and Release"
        ProductionRegex = '^forge[\\/]release[\\/]'
        TestRegex = '^tests[\\/].*release'
        DocumentationRegex = '^docs[\\/]releases[\\/]'
    }
    "M2.1" = @{
        Name = "Mission Planning"
        ProductionRegex = '^forge[\\/](planner|planning)[\\/]'
        TestRegex = '^tests[\\/].*(planner|planning|mission)'
        DocumentationRegex = '^docs[\\/].*(planner|planning|mission)'
    }
    "M2.2" = @{
        Name = "Task Management"
        ProductionRegex = '^forge[\\/]tasks[\\/]'
        TestRegex = '^tests[\\/].*task'
        DocumentationRegex = '^docs[\\/].*task'
    }
    "M2.3" = @{
        Name = "Impact Decision Engine"
        ProductionRegex = '^forge[\\/]impact[\\/]'
        TestRegex = '^tests[\\/].*impact'
        DocumentationRegex = '^docs[\\/].*impact'
    }
    "M2.4" = @{
        Name = "Engineering Memory"
        ProductionRegex = '^forge[\\/](engineering_memory|memory)[\\/]'
        TestRegex = '^tests[\\/].*memory'
        DocumentationRegex = '^docs[\\/].*memory'
    }
    "M2.5" = @{
        Name = "Mission Reporting"
        ProductionRegex = '^forge[\\/]mission_reporting[\\/]'
        TestRegex = '^tests[\\/].*(mission_reporting|report)'
        DocumentationRegex = '^docs[\\/].*(mission_reporting|report)'
    }
    "M3.1" = @{
        Name = "Execution Controller"
        ProductionRegex = '^forge[\\/]execution_controller[\\/]'
        TestRegex = '^tests[\\/]test_execution_controller_.*\.py$'
        DocumentationRegex = '^docs[\\/]execution_controller[\\/]'
    }
    "M3.2" = @{
        Name = "Safe Change Planning"
        ProductionRegex = '^forge[\\/]safe_change_planning[\\/]'
        TestRegex = '^tests[\\/].*safe_change_planning'
        DocumentationRegex = '^docs[\\/]safe_change_planning[\\/]'
    }

    "M3.3" = @{
        Name = "Safe Code Editing"
        ProductionRegex = '^forge[\\/]safe_code_editing[\\/]'
        TestRegex = '^tests[\\/]test_safe_code_editing_.*\.py$'
        DocumentationRegex = '^docs[\\/]safe_code_editing[\\/]'
    }

    "M3.4" = @{
        Name = "Validation and Repair Planning"
        ProductionRegex = '^forge[\\/]validation_repair[\\/]'
        TestRegex = '^tests[\\/]test_validation_repair_.*\.py$'
        DocumentationRegex = '^docs[\\/]validation_repair[\\/]'
    }

    "M3.5" = @{
        Name = "Autonomous Repair"
        ProductionRegex = '^forge[\\/]autonomous_repair[\\/]'
        TestRegex = '^tests[\\/]test_autonomous_repair_.*\.py$'
        DocumentationRegex = '^docs[\\/]autonomous_repair[\\/]'
    }

    "M3.6" = @{
        Name = "Engineering Mission Orchestration"
        ProductionRegex = '^forge[\\/]mission_orchestration[\\/]'
        TestRegex = '^tests[\\/]test_mission_orchestration_.*\.py$'
        DocumentationRegex = '^docs[\\/]mission_orchestration[\\/]'
    }
}

$Milestones = @()

foreach ($Milestone in $ExpectedMilestones) {
    $Phase = "Phase $($Milestone.Substring(1,1))"
    $Map = $MilestoneMap[$Milestone]

    $Production = @()
    $TestsForMilestone = @()
    $Docs = @()

    if ($Map) {
        $Production = @(
            $Inventory | Where-Object {
                $_.Classification -eq "production" -and
                $_.RelativePath -match $Map.ProductionRegex
            }
        )

        $TestsForMilestone = @(
            $TestInventory | Where-Object {
                $_.RelativePath -match $Map.TestRegex
            }
        )

        $Docs = @(
            $Inventory | Where-Object {
                $_.Classification -eq "documentation" -and
                $_.RelativePath -match $Map.DocumentationRegex
            }
        )
    }

    $Validations = @(
        $ValidationResults | Where-Object {
            $_.Milestone -eq $Milestone
        }
    )

    $TagPattern = $Milestone.Substring(1).Replace(".", "[\.\-_]?")
    $Tags = @(
        $Git.TagMap.Output | Where-Object {
            $_ -match "(?i)m$TagPattern"
        }
    )

    $HasProduction = $Production.Count -gt 0
    $HasTests = $TestsForMilestone.Count -gt 0
    $HasDocs = $Docs.Count -gt 0
    $ValidationPresent = $Validations.Count -gt 0
    $ValidationPass = $ValidationPresent -and (
        @($Validations | Where-Object Status -eq "FAIL").Count -eq 0
    )
    $HasTag = $Tags.Count -gt 0
    $OnMain = ($CurrentBranch -eq "main" -and $HeadCommit -eq $MainCommit)
    $QualityPass = ($Ruff.ExitCode -eq 0 -and $MyPy.ExitCode -eq 0)
    $TestsPass = ($Pytest.ExitCode -eq 0)

    $Status = "PLANNED"

    if (
        $HasProduction -and
        $HasTests -and
        $HasDocs -and
        $TestsPass -and
        $QualityPass -and
        ($ValidationPass -or -not $ValidationPresent) -and
        ($HasTag -or -not $ValidationPresent) -and
        $OnMain -and
        $WorkingTreeClean
    ) {
        $Status = if ($HasTag -or $ValidationPass) {
            "COMPLETE"
        }
        else {
            "IMPLEMENTED_NOT_RELEASED"
        }
    }
    elseif (
        $HasProduction -and
        $HasTests -and
        $TestsPass -and
        $QualityPass
    ) {
        $Status = "IMPLEMENTED_NOT_RELEASED"
    }
    elseif ($HasProduction -and ($HasTests -or $HasDocs)) {
        $Status = "PARTIALLY_IMPLEMENTED"
    }
    elseif ($HasProduction) {
        $Status = "SCAFFOLDED"
    }
    elseif ($HasDocs -or $ValidationPresent -or $HasTag) {
        $Status = "INCONSISTENT"
    }

    $Milestones += [pscustomobject]@{
        Milestone = $Milestone
        Name = if ($Map) { $Map.Name } else { "" }
        Phase = $Phase
        Status = $Status
        ProductionFiles = @($Production | ForEach-Object { $_.RelativePath })
        TestFiles = @($TestsForMilestone | ForEach-Object { $_.RelativePath })
        DocumentationFiles = @($Docs | ForEach-Object { $_.RelativePath })
        ProductionFileCount = $Production.Count
        TestFileCount = $TestsForMilestone.Count
        DocumentationFileCount = $Docs.Count
        ValidationPass = $ValidationPass
        ValidationPresent = $ValidationPresent
        TagPresent = $HasTag
        OnMain = $OnMain
        WorkingTreeClean = $WorkingTreeClean
    }
}

$PhaseDefinitions = @(
    [pscustomobject]@{Phase="Phase 0";Objective="Foundation";Deliverable="Repository Foundation";Weight=10},
    [pscustomobject]@{Phase="Phase 1";Objective="Engineering Runtime";Deliverable="Forge OS";Weight=20},
    [pscustomobject]@{Phase="Phase 2";Objective="Engineering Intelligence";Deliverable="AI Planning Engine";Weight=20},
    [pscustomobject]@{Phase="Phase 3";Objective="Engineering Execution";Deliverable="AI Software Engineer";Weight=25},
    [pscustomobject]@{Phase="Phase 4";Objective="ERP Expert";Deliverable="ERP Engineering Capability";Weight=15},
    [pscustomobject]@{Phase="Phase 5";Objective="Autonomous Platform";Deliverable="Production Engineering Platform";Weight=10}
)

$PhaseResults = @()

foreach ($Definition in $PhaseDefinitions) {
    if ($Definition.Phase -eq "Phase 0") {
        $FoundationComplete = (
            (Test-Path (Join-Path $RepositoryRoot "pyproject.toml")) -and
            (Test-Path (Join-Path $RepositoryRoot "README.md")) -and
            (Test-Path (Join-Path $RepositoryRoot ".gitignore")) -and
            (Test-Path (Join-Path $RepositoryRoot "forge")) -and
            (Test-Path (Join-Path $RepositoryRoot "tests"))
        )

        $Percent = if ($FoundationComplete) { 100 } else { 0 }

        $PhaseResults += [pscustomobject]@{
            Phase = $Definition.Phase
            Objective = $Definition.Objective
            Deliverable = $Definition.Deliverable
            Weight = $Definition.Weight
            ExpectedMilestones = 1
            Complete = if ($FoundationComplete) { 1 } else { 0 }
            Partial = if ($FoundationComplete) { 0 } else { 1 }
            Planned = 0
            Status = if ($FoundationComplete) { "COMPLETE" } else { "PARTIAL" }
            CompletionPercent = $Percent
            WeightedContribution = [math]::Round($Definition.Weight * $Percent / 100, 2)
        }
        continue
    }

    $Items = @($Milestones | Where-Object Phase -eq $Definition.Phase)
    $CompleteCount = @($Items | Where-Object Status -eq "COMPLETE").Count
    $PartialCount = @($Items | Where-Object {
        $_.Status -in @("IMPLEMENTED_NOT_RELEASED","PARTIALLY_IMPLEMENTED","SCAFFOLDED","INCONSISTENT")
    }).Count
    $PlannedCount = @($Items | Where-Object Status -eq "PLANNED").Count

    $Points = 0.0
    foreach ($Item in $Items) {
        switch ($Item.Status) {
            "COMPLETE" { $Points += 1.00 }
            "IMPLEMENTED_NOT_RELEASED" { $Points += 0.75 }
            "PARTIALLY_IMPLEMENTED" { $Points += 0.50 }
            "INCONSISTENT" { $Points += 0.25 }
            "SCAFFOLDED" { $Points += 0.20 }
        }
    }

    $Percent = if ($Items.Count -gt 0) {
        [math]::Round(($Points / $Items.Count) * 100, 2)
    } else { 0 }

    $PhaseResults += [pscustomobject]@{
        Phase = $Definition.Phase
        Objective = $Definition.Objective
        Deliverable = $Definition.Deliverable
        Weight = $Definition.Weight
        ExpectedMilestones = $Items.Count
        Complete = $CompleteCount
        Partial = $PartialCount
        Planned = $PlannedCount
        Status = if ($Items.Count -gt 0 -and $CompleteCount -eq $Items.Count) {
            "COMPLETE"
        } elseif ($Points -gt 0) {
            "PARTIAL"
        } else {
            "PLANNED"
        }
        CompletionPercent = $Percent
        WeightedContribution = [math]::Round($Definition.Weight * $Percent / 100, 2)
    }
}

$ProgrammeCompletion = [math]::Round(
    ($PhaseResults | Measure-Object WeightedContribution -Sum).Sum,
    2
)

$MilestoneCompletion = if ($Milestones.Count -gt 0) {
    [math]::Round(
        100 * @($Milestones | Where-Object Status -eq "COMPLETE").Count / $Milestones.Count,
        2
    )
} else { 0 }

$CapabilityCount = 0
$ImplementedCapabilityCount = 0
if ($CapabilityData -and $CapabilityData.capabilities) {
    $CapabilityCount = @($CapabilityData.capabilities).Count
    foreach ($Capability in @($CapabilityData.capabilities)) {
        $Json = $Capability | ConvertTo-Json -Depth 20 -Compress
        if (
            $Json -match '(?i)"implementation_status":"implemented"' -or
            $Json -match '(?i)"lifecycle":"available"'
        ) {
            $ImplementedCapabilityCount++
        }
    }
}

$CapabilityCompletion = if ($CapabilityCount -gt 0) {
    [math]::Round(100 * $ImplementedCapabilityCount / $CapabilityCount, 2)
} else { 0 }

$EvidenceMilestones = @(
    $Milestones | Where-Object {
        $_.ProductionFileCount -gt 0 -or
        $_.TestFileCount -gt 0 -or
        $_.DocumentationFileCount -gt 0 -or
        $_.ValidationPresent -or
        $_.TagPresent
    }
)

$HighestEvidence = $EvidenceMilestones |
    Sort-Object @{
        Expression = {
            $parts = $_.Milestone.Substring(1).Split(".")
            ([int]$parts[0] * 100) + [int]$parts[1]
        }
    } |
    Select-Object -Last 1

$Recommended = $null
if ($HighestEvidence) {
    $parts = $HighestEvidence.Milestone.Substring(1).Split(".")
    $nextMilestone = "M$($parts[0]).$([int]$parts[1] + 1)"
    $Recommended = $Milestones |
        Where-Object Milestone -eq $nextMilestone |
        Select-Object -First 1
}

if (-not $Recommended) {
    $Recommended = $Milestones |
        Where-Object Status -eq "PLANNED" |
        Sort-Object @{
            Expression = {
                $parts = $_.Milestone.Substring(1).Split(".")
                ([int]$parts[0] * 100) + [int]$parts[1]
            }
        } |
        Select-Object -First 1
}

$ProductionCount = @($Inventory | Where-Object Classification -eq "production").Count
$TestFileCount = @($Inventory | Where-Object Classification -eq "test").Count
$DocCount = @($Inventory | Where-Object Classification -eq "documentation").Count
$FailedValidationCount = @($ValidationResults | Where-Object Status -eq "FAIL").Count

$OverallStatus = if (
    $Pytest.ExitCode -ne 0 -or
    $Ruff.ExitCode -ne 0 -or
    $MyPy.ExitCode -ne 0
) {
    "FAIL"
}
elseif (
    -not $WorkingTreeClean -or
    $FailedValidationCount -gt 0 -or
    $Findings.Count -gt 0
) {
    "WARN"
}
else {
    "PASS"
}

# Risk report
$RiskLines = @(
    "# Aerion Forge Inconsistencies and Risks",
    "",
    "Generated: $(Get-Date -Format o)",
    ""
)

if ($Findings.Count -eq 0) {
    $RiskLines += "No inconsistencies were automatically detected."
}
else {
    foreach ($Severity in @("CRITICAL","HIGH","MEDIUM","LOW","INFORMATIONAL")) {
        $Items = @($Findings | Where-Object Severity -eq $Severity)
        if ($Items.Count -eq 0) { continue }

        $RiskLines += "## $Severity"
        $RiskLines += ""

        foreach ($Item in $Items) {
            $RiskLines += "- **$($Item.Area):** $($Item.Issue)"
            $RiskLines += "  - Evidence: $($Item.Evidence)"
        }

        $RiskLines += ""
    }
}
$RiskLines | Set-Content $RiskFile -Encoding utf8

# Markdown report
$Markdown = @(
    "# Aerion Forge Actual Progress Audit",
    "",
    "Generated: $(Get-Date -Format o)",
    "",
    "## 1. Executive Summary",
    "",
    "| Item | Result |",
    "|---|---|",
    "| Overall audit status | **$OverallStatus** |",
    "| Current branch | ``$CurrentBranch`` |",
    "| HEAD | ``$HeadCommit`` |",
    "| Local main | ``$MainCommit`` |",
    "| origin/main | ``$OriginMainCommit`` |",
    "| Working tree clean | $WorkingTreeClean |",
    "| Production files | $ProductionCount |",
    "| Test files | $TestFileCount |",
    "| Documentation files | $DocCount |",
    "| Validation scripts | $($ValidationScripts.Count) |",
    "| Failed validation scripts | $FailedValidationCount |",
    "| Tests collected | $Collected |",
    "| Tests passed | $Passed |",
    "| Tests failed | $Failed |",
    "| Ruff | $($Ruff.Status) |",
    "| MyPy | $($MyPy.Status) |",
    "| pytest | $($Pytest.Status) |",
    "| Milestone completion | $MilestoneCompletion% |",
    "| Capability implementation | $CapabilityCompletion% |",
    "| Programme weighted completion | $ProgrammeCompletion% |",
    "| Recommended next milestone | $(if($Recommended){$Recommended.Milestone}else{'None identified'}) |",
    "",
    "## 2. Phase 0-5 Dashboard",
    "",
    "| Phase | Objective | Deliverable | Expected Milestones | Complete | Partial | Planned | Status | Completion | Weighted Contribution |",
    "|---|---|---|---:|---:|---:|---:|---|---:|---:|"
)

foreach ($Phase in $PhaseResults) {
    $Markdown += "| $($Phase.Phase) | $($Phase.Objective) | $($Phase.Deliverable) | $($Phase.ExpectedMilestones) | $($Phase.Complete) | $($Phase.Partial) | $($Phase.Planned) | $($Phase.Status) | $($Phase.CompletionPercent)% | $($Phase.WeightedContribution)% |"
}

$Markdown += @(
    "",
    "## 3. Milestone Evidence",
    "",
    "| Milestone | Phase | Status | Production | Tests | Docs | Validation | Tag | On main |",
    "|---|---|---|---:|---:|---:|---|---|---|"
)

foreach ($Milestone in $Milestones) {
    $Markdown += "| $($Milestone.Milestone) | $($Milestone.Phase) | $($Milestone.Status) | $($Milestone.ProductionFileCount) | $($Milestone.TestFileCount) | $($Milestone.DocumentationFileCount) | $($Milestone.ValidationPass) | $($Milestone.TagPresent) | $($Milestone.OnMain) |"
}

$Markdown += @(
    "",
    "## 4. Capability Registry",
    "",
    "- Catalogue status: $(if($CapabilityData){$CapabilityData.status}else{'NOT LOADED'})",
    "- Capabilities found: $CapabilityCount",
    "- Capabilities implemented or available: $ImplementedCapabilityCount",
    "- Detailed data: ``audit\AERION_FORGE_CAPABILITY_REGISTRY.json``",
    "",
    "## 5. Test and Quality Evidence",
    "",
    "| Check | Status | Exit Code | Duration |",
    "|---|---|---:|---:|",
    "| Ruff | $($Ruff.Status) | $($Ruff.ExitCode) | $($Ruff.DurationSeconds)s |",
    "| MyPy | $($MyPy.Status) | $($MyPy.ExitCode) | $($MyPy.DurationSeconds)s |",
    "| pytest | $($Pytest.Status) | $($Pytest.ExitCode) | $($Pytest.DurationSeconds)s |",
    "",
    "## 6. Inconsistencies and Risks",
    "",
    "- Total findings: $($Findings.Count)",
    "- Detailed report: ``audit\AERION_FORGE_INCONSISTENCIES.md``",
    "",
    "## 7. Recommended Next Step",
    ""
)

if ($Recommended) {
    $Markdown += @(
        "### $($Recommended.Milestone)",
        "",
        "- Current status: $($Recommended.Status)",
        "- Objective: close the earliest incomplete milestone before advancing.",
        "- Acceptance gate: implementation, documentation, tests, Ruff, MyPy, validation scripts, capability registry, final tag, main-branch presence, and a clean working tree."
    )
}
else {
    $Markdown += "No incomplete milestone was identified."
}

$Markdown += @(
    "",
    "## 8. Generated Evidence Files",
    "",
    "- ``audit\AERION_FORGE_PROGRESS_AUDIT.md``",
    "- ``audit\AERION_FORGE_PROGRESS_AUDIT.json``",
    "- ``audit\AERION_FORGE_FILE_INVENTORY.csv``",
    "- ``audit\AERION_FORGE_TEST_INVENTORY.csv``",
    "- ``audit\AERION_FORGE_GIT_EVIDENCE.txt``",
    "- ``audit\AERION_FORGE_CAPABILITY_REGISTRY.json``",
    "- ``audit\AERION_FORGE_VALIDATION_RESULTS.txt``",
    "- ``audit\AERION_FORGE_INCONSISTENCIES.md``"
)

$Markdown | Set-Content $ReportMd -Encoding utf8

# JSON report
$Ended = Get-Date
$Payload = [ordered]@{
    audit_metadata = [ordered]@{
        repository_root = $RepositoryRoot
        started_at = $Started.ToString("o")
        completed_at = $Ended.ToString("o")
        duration_seconds = [math]::Round(($Ended - $Started).TotalSeconds, 2)
        overall_status = $OverallStatus
    }
    git = [ordered]@{
        current_branch = $CurrentBranch
        head = $HeadCommit
        main = $MainCommit
        origin_main = $OriginMainCommit
        working_tree_clean = $WorkingTreeClean
        tags = $Git.Tags.Output
        tag_mapping = $Git.TagMap.Output
        recent_commits = $Git.RecentCommits.Output
    }
    quality = [ordered]@{
        ruff = $Ruff
        mypy = $MyPy
    }
    tests = [ordered]@{
        collected = $Collected
        passed = $Passed
        failed = $Failed
        skipped = $Skipped
        xfailed = $XFailed
        xpassed = $XPassed
        result = $Pytest
        inventory = $TestInventory
    }
    validation_scripts = $ValidationResults
    files = [ordered]@{
        total = $Inventory.Count
        production = $ProductionCount
        tests = $TestFileCount
        documentation = $DocCount
        empty = $EmptyFiles.Count
        inventory = $Inventory
    }
    capabilities = $CapabilityData
    milestones = $Milestones
    phases = $PhaseResults
    progress = [ordered]@{
        milestone_completion_percentage = $MilestoneCompletion
        capability_implementation_percentage = $CapabilityCompletion
        programme_weighted_completion_percentage = $ProgrammeCompletion
    }
    source_markers = $Markers
    inconsistencies = $Findings
    recommended_next_step = if ($Recommended) {
        [ordered]@{
            milestone = $Recommended.Milestone
            status = $Recommended.Status
        }
    } else { $null }
}

$Payload | ConvertTo-Json -Depth 100 |
    Set-Content $ReportJson -Encoding utf8

Write-Host ""
Write-Host ("=" * 80) -ForegroundColor DarkGray
Write-Host "AERION FORGE AUDIT COMPLETE" -ForegroundColor Green
Write-Host ("=" * 80) -ForegroundColor DarkGray
Write-Host "Overall status: $OverallStatus"
Write-Host "Programme completion: $ProgrammeCompletion%"
Write-Host "Milestone completion: $MilestoneCompletion%"
Write-Host "Capability implementation: $CapabilityCompletion%"
Write-Host ""
Write-Host "Primary report:"
Write-Host "  $ReportMd"
Write-Host ""
Write-Host "Open it with:"
Write-Host "  code `"$ReportMd`""
Write-Host ""

exit 0
