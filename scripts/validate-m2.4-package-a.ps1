$RequiredFiles = @(
    "forge\engineering_memory\errors.py",
    "forge\engineering_memory\models.py",
    "forge\engineering_memory\identifiers.py",
    "forge\engineering_memory\policies.py",
    "forge\engineering_memory\validator.py",
    "tests\test_engineering_memory_models.py",
    "tests\test_engineering_memory_identifiers_policies.py",
    "tests\test_engineering_memory_validation.py"
)

$Problems = foreach ($File in $RequiredFiles) {
    if (-not (Test-Path $File)) {
        "MISSING: $File"
    }
    elseif ((Get-Item $File).Length -eq 0) {
        "EMPTY: $File"
    }
}

if ($Problems) {
    $Problems
    throw "M2.4 Package A is incomplete."
}

$TestCount = (
    Select-String `
        -Path tests\test_engineering_memory_*.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 30) {
    throw "M2.4 Package A has only $TestCount tests; minimum is 30."
}

Write-Host "M2.4 Package A populated with $TestCount tests." -ForegroundColor Green
