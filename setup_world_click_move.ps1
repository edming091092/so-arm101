$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "work\lerobot_py312\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Python environment was not found." -ForegroundColor Red
    Write-Host "Run setup_lerobot_windows.ps1 first:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\setup_lerobot_windows.ps1"
    exit 1
}

Write-Host "Installing camera-world click-move dependencies into:"
Write-Host $VenvPython
Write-Host ""

& $VenvPython -m pip install --upgrade numpy opencv-python pillow

New-Item -ItemType Directory -Force -Path (Join-Path $RepoRoot "calibration") | Out-Null

Write-Host ""
Write-Host "Camera-world click-move setup complete."
Write-Host "Run:"
Write-Host '& ".\work\lerobot_py312\Scripts\python.exe" ".\camera_world_click_move.py" --arm-set-id lab01 --follower-port COM5 --leader-port COM4 --camera 0'
