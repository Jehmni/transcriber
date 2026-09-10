<#
    Stribe installer.

    Default: copies the app into %LOCALAPPDATA%\Programs\Stribe, creates the
    Desktop and Start menu shortcuts, and registers Stribe in Windows
    "Installed apps" so it can be uninstalled the normal way.

    Usage:
        powershell -ExecutionPolicy Bypass -File install.ps1
        powershell -ExecutionPolicy Bypass -File install.ps1 -InPlace
#>
param(
    [switch]$InPlace,   # run from the current folder instead of copying (for development)
    [switch]$Quiet      # no prompts; fail rather than ask
)

$ErrorActionPreference = 'Stop'

$AppName   = 'Stribe'
$Publisher = 'Stargit Solutions'
$Version   = '1.0.0'

$sourceDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ''
Write-Host "  Installing $AppName $Version" -ForegroundColor Cyan
Write-Host '  Audio to text, entirely on your machine'
Write-Host ''

# ---------------------------------------------------------------- Python ----
function Find-Python {
    foreach ($candidate in @('python.exe', 'python3.exe')) {
        $cmd = Get-Command $candidate -ErrorAction SilentlyContinue
        if ($cmd) {
            $v = & $cmd.Source -c "import sys; print('%d.%d' % sys.version_info[:2])" 2>$null
            if ($LASTEXITCODE -eq 0 -and [version]$v -ge [version]'3.9') { return $cmd.Source }
        }
    }
    return $null
}

$py = Find-Python

if (-not $py) {
    Write-Host '  Python 3.9+ was not found on this computer.' -ForegroundColor Yellow
    $winget = Get-Command winget.exe -ErrorAction SilentlyContinue
    $install = $false

    if ($winget -and -not $Quiet) {
        $answer = Read-Host '  Install Python automatically now? [Y/n]'
        $install = ($answer -eq '' -or $answer -match '^(y|yes)$')
    } elseif ($winget -and $Quiet) {
        $install = $true
    }

    if ($install) {
        Write-Host '  Installing Python (this takes a few minutes)...'
        & winget install --id Python.Python.3.12 --source winget `
            --accept-package-agreements --accept-source-agreements -h
        # winget updates PATH for new processes only, so look in the usual place too.
        $env:PATH = "$env:LOCALAPPDATA\Programs\Python\Python312;$env:LOCALAPPDATA\Programs\Python\Python312\Scripts;$env:PATH"
        $py = Find-Python
    }

    if (-not $py) {
        Write-Host ''
        Write-Host '  Install Python 3.9 or newer, then run this installer again.' -ForegroundColor Yellow
        Write-Host '  Download: https://www.python.org/downloads/'
        Write-Host '  Tick "Add python.exe to PATH" during setup.'
        throw 'Python is required.'
    }
}

Write-Host "  Python: $py"

# ---------------------------------------------------------- dependencies ----
Write-Host '  Checking dependencies...'
& $py -c "import whisper, torch, PIL" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '  Installing openai-whisper, torch and Pillow.'
    Write-Host '  This downloads roughly 1 GB and can take several minutes.' -ForegroundColor Yellow
    & $py -m pip install --upgrade --disable-pip-version-check -r (Join-Path $sourceDir 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
} else {
    Write-Host '  Dependencies already present.'
}

# ------------------------------------------------------------- copy files ----
if ($InPlace) {
    $installDir = $sourceDir
    Write-Host "  Running in place: $installDir"
} else {
    $installDir = Join-Path $env:LOCALAPPDATA "Programs\$AppName"
    Write-Host "  Installing to: $installDir"

    if (Test-Path $installDir) {
        # Leave anything the user created (saved transcripts) alone.
        foreach ($item in @('app.py', 'theme.py', 'widgets.py', 'transcribe.py',
                            'requirements.txt', 'README.md', 'assets')) {
            $path = Join-Path $installDir $item
            if (Test-Path $path) { Remove-Item $path -Recurse -Force }
        }
    }
    New-Item -ItemType Directory -Path $installDir -Force | Out-Null

    foreach ($item in @('app.py', 'theme.py', 'widgets.py', 'transcribe.py',
                        'requirements.txt', 'README.md', 'uninstall.ps1',
                        'Uninstall Stribe.bat', 'ffmpeg.exe')) {
        $src = Join-Path $sourceDir $item
        if (Test-Path $src) { Copy-Item $src -Destination $installDir -Force }
    }
    Copy-Item (Join-Path $sourceDir 'assets') -Destination $installDir -Recurse -Force
}

$appPy = Join-Path $installDir 'app.py'
$icon  = Join-Path $installDir 'assets\stribe.ico'

$pyw = Join-Path (Split-Path -Parent $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }

# -------------------------------------------------------------- shortcuts ----
$desktop   = [Environment]::GetFolderPath('Desktop')
$startMenu = [IO.Path]::Combine([Environment]::GetFolderPath('StartMenu'), 'Programs')

foreach ($stale in @((Join-Path $desktop 'Audio Transcriber.lnk'),
                     (Join-Path $startMenu 'Audio Transcriber.lnk'))) {
    if (Test-Path $stale) { Remove-Item $stale -Force }
}

$shell = New-Object -ComObject WScript.Shell
foreach ($target in @((Join-Path $desktop "$AppName.lnk"), (Join-Path $startMenu "$AppName.lnk"))) {
    $parent = Split-Path -Parent $target
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }

    $lnk = $shell.CreateShortcut($target)
    $lnk.TargetPath       = $pyw
    $lnk.Arguments        = '"' + $appPy + '"'
    $lnk.WorkingDirectory = $installDir
    $lnk.IconLocation     = if (Test-Path $icon) { $icon } else { "$pyw,0" }
    $lnk.Description      = 'Transcribe audio to text, entirely on your machine'
    $lnk.Save()
    Write-Host "  Shortcut: $target"
}

# ------------------------------------------ register in "Installed apps" ----
if (-not $InPlace) {
    $key = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\$AppName"
    New-Item -Path $key -Force | Out-Null
    $uninstall = "powershell -ExecutionPolicy Bypass -File `"$(Join-Path $installDir 'uninstall.ps1')`""
    $size = [int]((Get-ChildItem $installDir -Recurse -File |
                   Measure-Object -Property Length -Sum).Sum / 1KB)

    New-ItemProperty -Path $key -Name 'DisplayName'     -Value $AppName   -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DisplayVersion'  -Value $Version   -Force | Out-Null
    New-ItemProperty -Path $key -Name 'Publisher'       -Value $Publisher -Force | Out-Null
    New-ItemProperty -Path $key -Name 'DisplayIcon'     -Value $icon      -Force | Out-Null
    New-ItemProperty -Path $key -Name 'InstallLocation' -Value $installDir -Force | Out-Null
    New-ItemProperty -Path $key -Name 'UninstallString' -Value $uninstall -Force | Out-Null
    New-ItemProperty -Path $key -Name 'NoModify'        -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name 'NoRepair'        -Value 1 -PropertyType DWord -Force | Out-Null
    New-ItemProperty -Path $key -Name 'EstimatedSize'   -Value $size -PropertyType DWord -Force | Out-Null
    Write-Host "  Registered in Installed apps as `"$AppName`""
}

Write-Host ''
Write-Host "  $AppName is installed." -ForegroundColor Green
Write-Host '  Launch it from your Desktop or the Start menu.'
Write-Host ''
