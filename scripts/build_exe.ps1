param(
    [switch]$OneFile
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

if (-not (Test-Path ".\.venv\Scripts\python.exe")) {
    throw "Virtual environment not found at .venv. Create it first with 'python -m venv .venv'."
}

$python = ".\.venv\Scripts\python.exe"

& $python -m pip install --upgrade pip
& $python -m pip install -r requirements.txt
& $python -m pip install pyinstaller

if ($OneFile) {
    & $python -m PyInstaller --noconfirm --clean --onefile --windowed --name MissionManager --paths src launcher.py
} else {
    & $python -m PyInstaller --noconfirm --clean MissionManager.spec
}

if ($OneFile) {
    Write-Host "Built dist\MissionManager.exe"
} else {
    Write-Host "Built dist\MissionManager\MissionManager.exe"
}
