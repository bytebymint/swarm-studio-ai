param([switch]$SkipTests)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $projectRoot
$pythonPath = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $pythonPath)) { throw 'Install requirements into .venv first.' }
if (-not $SkipTests) {
    $testRoot = Join-Path $projectRoot 'test-results'
    New-Item -ItemType Directory -Path $testRoot -Force | Out-Null
    $testTemp = Join-Path $testRoot ('build-unit-' + [guid]::NewGuid().ToString('N'))
    & $pythonPath -m pytest -q --basetemp $testTemp
    if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
}
& $pythonPath scripts/make_icon.py
if ($LASTEXITCODE -ne 0) { throw 'Icon generation failed.' }
& $pythonPath -m PyInstaller --noconfirm SwarmStudio.spec
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
$appFolder = Join-Path $projectRoot 'dist\SwarmStudio'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install_windows.ps1') -Destination $appFolder
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination $appFolder
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination $appFolder
