<#
    Removes Stribe: shortcuts, the "Installed apps" entry, and the program
    folder. Downloaded Whisper models in ~/.cache/whisper are left alone -
    they are shared with any other Whisper tool and are expensive to refetch.
#>
param([switch]$Quiet)

$ErrorActionPreference = 'Stop'

$AppName = 'Stribe'
$installDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"

Write-Host ''
Write-Host "  Uninstalling $AppName" -ForegroundColor Cyan

if (-not $Quiet) {
    $answer = Read-Host "  Remove $AppName from this computer? [y/N]"
    if ($answer -notmatch '^(y|yes)$') { Write-Host '  Cancelled.'; return }
}

$desktop   = [Environment]::GetFolderPath('Desktop')
$startMenu = [IO.Path]::Combine([Environment]::GetFolderPath('StartMenu'), 'Programs')
foreach ($lnk in @((Join-Path $desktop "$AppName.lnk"), (Join-Path $startMenu "$AppName.lnk"))) {
    if (Test-Path $lnk) { Remove-Item $lnk -Force; Write-Host "  Removed shortcut: $lnk" }
}

$key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
if (Test-Path $key) { Remove-Item $key -Recurse -Force; Write-Host '  Removed Installed apps entry' }

if (Test-Path $installDir) {
    # The uninstaller lives inside the folder it is deleting, so hand the
    # delete to a detached process that runs once this one has exited.
    $cmd = "Start-Sleep -Seconds 2; Remove-Item -LiteralPath '$installDir' -Recurse -Force -ErrorAction SilentlyContinue"
    Start-Process powershell -ArgumentList '-NoProfile', '-WindowStyle', 'Hidden', '-Command', $cmd | Out-Null
    Write-Host "  Removing $installDir"
}

Write-Host ''
Write-Host "  $AppName has been removed." -ForegroundColor Green
Write-Host '  Downloaded speech models were kept in ~\.cache\whisper.'
Write-Host ''
