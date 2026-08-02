$Files = @(
    "forge\execution_controller\builder.py",
    "forge\execution_controller\renderer.py",
    "forge\execution_controller\service.py",
    "tests\test_execution_controller_builder.py",
    "tests\test_execution_controller_renderer.py",
    "tests\test_execution_controller_service.py"
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
    throw "M3.1 Package B is incomplete."
}

$TestCount = (
    Select-String `
        -Path `
            tests\test_execution_controller_builder.py, `
            tests\test_execution_controller_renderer.py, `
            tests\test_execution_controller_service.py `
        -Pattern "^def test_"
).Count

if ($TestCount -lt 50) {
    throw "M3.1 Package B has only $TestCount tests; minimum is 50."
}

Write-Host "M3.1 Package B populated with $TestCount tests." -ForegroundColor Green
