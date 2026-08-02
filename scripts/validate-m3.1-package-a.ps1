$Files = @(
    "forge\execution_controller\models.py",
    "forge\execution_controller\identifiers.py",
    "forge\execution_controller\policies.py",
    "forge\execution_controller\validator.py",
    "tests\test_execution_controller_models.py",
    "tests\test_execution_controller_identifiers.py",
    "tests\test_execution_controller_validator.py"
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
    throw "M3.1 Package A is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_execution_controller_models.py, `
            tests\test_execution_controller_identifiers.py, `
            tests\test_execution_controller_validator.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 40) {
    throw "M3.1 Package A has only $TestCount tests; minimum is 40."
}

Write-Host "M3.1 Package A populated with $TestCount tests." -ForegroundColor Green
