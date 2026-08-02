$Files = @(
    "forge\engineering_memory\renderer.py",
    "forge\engineering_memory\service.py",
    "tests\test_engineering_memory_renderer.py",
    "tests\test_engineering_memory_service.py"
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
    throw "M2.4 Batch B2 is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_engineering_memory_renderer.py, `
            tests\test_engineering_memory_service.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 20) {
    throw "M2.4 Batch B2 has only $TestCount tests; minimum is 20."
}

Write-Host "M2.4 Batch B2 populated with $TestCount tests." -ForegroundColor Green
