$Files = @(
    "forge\safe_change_planning\cli.py",
    "tests\test_safe_change_planning_cli.py"
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
    throw "M3.2 completion package is incomplete."
}

$TestCount = (
    Select-String `
        -Path tests\test_safe_change_planning_cli.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 20) {
    throw "Safe Change Planning CLI has only $TestCount tests; minimum is 20."
}

Write-Host "M3.2 completion package populated with $TestCount CLI tests." -ForegroundColor Green
