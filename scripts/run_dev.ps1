param([switch]$Demo)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Create the virtual environment and install requirements first. See README.md.'
}
if ($Demo) { & $pythonPath main.py --demo } else { & $pythonPath main.py }
exit $LASTEXITCODE
