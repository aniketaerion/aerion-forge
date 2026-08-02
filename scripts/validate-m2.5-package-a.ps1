$Files = @(
    "forge\mission_reporting\errors.py",
    "forge\mission_reporting\models.py",
    "forge\mission_reporting\identifiers.py",
    "forge\mission_reporting\policies.py",
    "forge\mission_reporting\validator.py",
    "tests\test_mission_reporting_models.py",
    "tests\test_mission_reporting_identifiers_policies.py",
    "tests\test_mission_reporting_validation.py"
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
    throw "M2.5 Package A is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_mission_reporting_models.py, `
            tests\test_mission_reporting_identifiers_policies.py, `
            tests\test_mission_reporting_validation.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 30) {
    throw "M2.5 Package A has only $TestCount tests; minimum is 30."
}

Write-Host "M2.5 Package A populated with $TestCount tests." -ForegroundColor Green
