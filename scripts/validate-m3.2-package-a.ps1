$Files = @(
    "forge\safe_change_planning\models.py",
    "forge\safe_change_planning\identifiers.py",
    "forge\safe_change_planning\policies.py",
    "forge\safe_change_planning\validator.py",
    "tests\test_safe_change_planning_models.py",
    "tests\test_safe_change_planning_identifiers.py",
    "tests\test_safe_change_planning_validator.py"
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
    throw "M3.2 Package A is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_safe_change_planning_models.py, `
            tests\test_safe_change_planning_identifiers.py, `
            tests\test_safe_change_planning_validator.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 40) {
    throw "M3.2 Package A has only $TestCount tests; minimum is 40."
}

Write-Host "M3.2 Package A populated with $TestCount tests." -ForegroundColor Green
