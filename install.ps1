# Lumen Studio – Download & Start
#   irm https://raw.githubusercontent.com/Dodovking/bildwerkstatt/main/install.ps1 | iex
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$ziel = Join-Path ([Environment]::GetFolderPath('UserProfile')) 'Downloads\Lumen.exe'
Write-Host 'Lade Lumen Studio …' -ForegroundColor Magenta
Invoke-WebRequest 'https://github.com/Dodovking/bildwerkstatt/releases/latest/download/Lumen.exe' -OutFile $ziel -UseBasicParsing
Start-Process $ziel
