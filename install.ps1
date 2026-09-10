# Installs Stribe on this laptop.
# Run with:  powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = 'Stop'

$appDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPy  = Join-Path $appDir 'app.py'
$icon   = Join-Path $appDir 'assets\stribe.ico'

if (-not (Test-Path $appPy)) { throw "app.py not found in $appDir" }

# python.exe for the checks (PowerShell waits on console apps and gets a real
# exit code); pythonw.exe as the shortcut target so no console window appears.
$py = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $py) { throw 'Python was not found on PATH. Install Python 3.10+ and retry.' }

$pyw = Join-Path (Split-Path -Parent $py) 'pythonw.exe'
if (-not (Test-Path $pyw)) { $pyw = $py }

Write-Host "Using interpreter: $py"

Write-Host 'Checking dependencies (openai-whisper, torch, Pillow)...'
& $py -c "import whisper, torch, PIL" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host 'Installing dependencies (this can take several minutes)...'
    & $py -m pip install --upgrade -r (Join-Path $appDir 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'pip install failed.' }
} else {
    Write-Host 'Dependencies already installed.'
}

$desktop   = [Environment]::GetFolderPath('Desktop')
$startMenu = [IO.Path]::Combine([Environment]::GetFolderPath('StartMenu'), 'Programs')

# Clear out shortcuts from the previous name so there is only one entry.
foreach ($stale in @(
    (Join-Path $desktop   'Audio Transcriber.lnk'),
    (Join-Path $startMenu 'Audio Transcriber.lnk')
)) {
    if (Test-Path $stale) {
        Remove-Item $stale -Force
        Write-Host "Removed old shortcut: $stale"
    }
}

$shell = New-Object -ComObject WScript.Shell
foreach ($target in @((Join-Path $desktop 'Stribe.lnk'), (Join-Path $startMenu 'Stribe.lnk'))) {
    $parent = Split-Path -Parent $target
    if (-not (Test-Path $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }

    $lnk = $shell.CreateShortcut($target)
    $lnk.TargetPath       = $pyw
    $lnk.Arguments        = '"' + $appPy + '"'
    $lnk.WorkingDirectory = $appDir
    $lnk.IconLocation     = if (Test-Path $icon) { $icon } else { "$pyw,0" }
    $lnk.Description      = 'Transcribe audio to text, entirely on your machine'
    $lnk.Save()
    Write-Host "Created shortcut: $target"
}

Write-Host ''
Write-Host 'Done. Launch "Stribe" from your Desktop or the Start menu.'
