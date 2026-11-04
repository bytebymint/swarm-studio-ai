param([string]$Destination = (Join-Path $env:LOCALAPPDATA 'Programs\SwarmStudio'))
$ErrorActionPreference = 'Stop'
$source = [System.IO.Path]::GetFullPath($PSScriptRoot)
if (-not (Test-Path -LiteralPath (Join-Path $source 'SwarmStudio.exe'))) {
    throw 'Run this installer from the built SwarmStudio distribution folder.'
}
