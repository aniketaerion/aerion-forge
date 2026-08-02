$Files = @(
    "forge\mission_reporting\cli.py",
    "tests\test_mission_reporting_cli.py",
    "docs\MISSION_REPORTING.md",
    "docs\contracts\MISSION_REPORTING_CONTRACT.md"
)

$Problems = foreach ($File in $Files) {
    if (-not (Test-Path $File)) {
        "MISSING: $File"
    }
    elseif ((Get-Item $File).Length -eq 0) {
        "EMPTY: $File"
    }
}

if ($Problems) {
    $Problems
    throw "M2.5 completion package is incomplete."
}

$TestCount = (
    Select-String `
        -Path tests\test_mission_reporting_cli.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 18) {
    throw "Mission Reporting CLI has only $TestCount tests; minimum is 18."
}

Write-Host "M2.5 completion package populated with $TestCount CLI tests." -ForegroundColor Green
