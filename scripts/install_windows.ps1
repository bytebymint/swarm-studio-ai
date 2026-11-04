param([string]$Destination = (Join-Path $env:LOCALAPPDATA 'Programs\SwarmStudio'))
$ErrorActionPreference = 'Stop'
$source = [System.IO.Path]::GetFullPath($PSScriptRoot)
