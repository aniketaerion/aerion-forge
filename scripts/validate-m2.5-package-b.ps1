$Files = @(
    "forge\mission_reporting\builder.py",
    "forge\mission_reporting\renderer.py",
    "forge\mission_reporting\service.py",
    "tests\test_mission_reporting_builder.py",
    "tests\test_mission_reporting_renderer.py",
    "tests\test_mission_reporting_service.py"
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
    throw "M2.5 Package B is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_mission_reporting_builder.py, `
            tests\test_mission_reporting_renderer.py, `
            tests\test_mission_reporting_service.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 30) {
    throw "M2.5 Package B has only $TestCount tests; minimum is 30."
}

Write-Host "M2.5 Package B populated with $TestCount tests." -ForegroundColor Green
