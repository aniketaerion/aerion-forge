$Files = @(
    "forge\engineering_memory\builder.py",
    "forge\engineering_memory\store.py",
    "forge\engineering_memory\query.py",
    "tests\test_engineering_memory_builder.py",
    "tests\test_engineering_memory_store.py",
    "tests\test_engineering_memory_query.py"
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
    throw "M2.4 Batch B1 is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_engineering_memory_builder.py, `
            tests\test_engineering_memory_store.py, `
            tests\test_engineering_memory_query.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 24) {
    throw "M2.4 Batch B1 has only $TestCount tests; minimum is 24."
}

Write-Host "M2.4 Batch B1 populated with $TestCount tests." -ForegroundColor Green
