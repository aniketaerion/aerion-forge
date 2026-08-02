$Files = @(
    "forge\safe_change_planning\builder.py",
    "forge\safe_change_planning\renderer.py",
    "forge\safe_change_planning\service.py",
    "tests\test_safe_change_planning_builder.py",
    "tests\test_safe_change_planning_renderer.py",
    "tests\test_safe_change_planning_service.py"
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
    throw "M3.2 Package B is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_safe_change_planning_builder.py, `
            tests\test_safe_change_planning_renderer.py, `
            tests\test_safe_change_planning_service.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 50) {
    throw "M3.2 Package B has only $TestCount tests; minimum is 50."
}

Write-Host "M3.2 Package B populated with $TestCount tests." -ForegroundColor Green
