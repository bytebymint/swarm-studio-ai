param([string]$Destination = (Join-Path $env:LOCALAPPDATA 'Programs\SwarmStudio'))
$ErrorActionPreference = 'Stop'
$source = [System.IO.Path]::GetFullPath($PSScriptRoot)
if (-not (Test-Path -LiteralPath (Join-Path $source 'SwarmStudio.exe'))) {
    throw 'Run this installer from the built SwarmStudio distribution folder.'
}
$destinationPath = [System.IO.Path]::GetFullPath($Destination)
if ($destinationPath -eq $source) { throw 'Choose an install folder different from the distribution folder.' }
New-Item -ItemType Directory -Path $destinationPath -Force | Out-Null
Get-ChildItem -LiteralPath $source | Copy-Item -Destination $destinationPath -Recurse -Force
$shortcutRoot = Join-Path $env:APPDATA 'Microsoft\Windows\Start Menu\Programs'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut((Join-Path $shortcutRoot 'Swarm Studio.lnk'))
$shortcut.TargetPath = Join-Path $destinationPath 'SwarmStudio.exe'
$shortcut.WorkingDirectory = $destinationPath
$shortcut.Description = 'Swarm Studio website reconstruction desk'
$shortcut.Save()
