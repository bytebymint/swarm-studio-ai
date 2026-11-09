param([switch]$SkipTests, [switch]$Portable)
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
if ($Portable) {
    $browserDirectory = Join-Path $projectRoot 'build\portable-browsers'
    $noticeDirectory = Join-Path $projectRoot 'build\portable-notices'
    $previousBrowserPath = $env:PLAYWRIGHT_BROWSERS_PATH
    try {
        $env:PLAYWRIGHT_BROWSERS_PATH = $browserDirectory
        & $pythonPath -m playwright install chromium --only-shell
        if ($LASTEXITCODE -ne 0) { throw 'Could not prepare the portable recording browser.' }
    } finally { $env:PLAYWRIGHT_BROWSERS_PATH = $previousBrowserPath }
    & $pythonPath scripts/collect_licenses.py --output $noticeDirectory
    if ($LASTEXITCODE -ne 0) { throw 'Could not collect portable dependency notices.' }
}
$previousOneFile = $env:SWARM_STUDIO_ONEFILE
try {
    $env:SWARM_STUDIO_ONEFILE = if ($Portable) { '1' } else { '0' }
    & $pythonPath -m PyInstaller --noconfirm SwarmStudio.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller failed.' }
} finally { $env:SWARM_STUDIO_ONEFILE = $previousOneFile }
if ($Portable) {
    & $pythonPath scripts/verify_public_build.py --exe dist/SwarmStudioAI-Portable.exe
    if ($LASTEXITCODE -ne 0) { throw 'Public build verification failed.' }
    Write-Host 'Built dist\SwarmStudioAI-Portable.exe - a single executable; no installer or sidecar folder is needed.'
    exit 0
}
$appFolder = Join-Path $projectRoot 'dist\SwarmStudio'
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'install_windows.ps1') -Destination $appFolder
Copy-Item -LiteralPath (Join-Path $projectRoot 'README.md') -Destination $appFolder
Copy-Item -LiteralPath (Join-Path $projectRoot 'LICENSE') -Destination $appFolder
Copy-Item -LiteralPath (Join-Path $projectRoot 'THIRD_PARTY_NOTICES.md') -Destination $appFolder
Copy-Item -LiteralPath (Join-Path $projectRoot 'docs') -Destination $appFolder -Recurse -Force
Copy-Item -LiteralPath (Join-Path $projectRoot 'requirements-lock.txt') -Destination $appFolder
& $pythonPath scripts/collect_licenses.py
if ($LASTEXITCODE -ne 0) { throw 'Could not collect dependency notices.' }
Write-Host "Built $appFolder\SwarmStudio.exe"
Write-Host 'Run install_windows.ps1 inside that folder to install for the current user.'
