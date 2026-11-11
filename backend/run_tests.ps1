$repoRoot = Split-Path -Parent $PSScriptRoot
$pyExe = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $pyExe)) {
    $pyExe = "python"
}
Set-Location $PSScriptRoot
& $pyExe -m pytest tests/ -v 2>&1
