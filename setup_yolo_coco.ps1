param(
    [ValidateSet("auto", "cpu", "gpu", "cuda")]
    [string]$Device = "auto"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "work\lerobot_py312\Scripts\python.exe"
$TorchSetupScript = Join-Path $RepoRoot "setup_pytorch_device.ps1"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Python environment was not found." -ForegroundColor Red
    Write-Host "Run setup_lerobot_windows.ps1 first:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\setup_lerobot_windows.ps1"
    exit 1
}

Write-Host "Installing YOLO COCO dependencies into:"
Write-Host $VenvPython
Write-Host ""

& $TorchSetupScript -Device $Device
& $VenvPython -m pip install --upgrade ultralytics pillow

Write-Host ""
Write-Host "YOLO COCO setup complete."
Write-Host "Run:"
Write-Host '& ".\work\lerobot_py312\Scripts\python.exe" ".\yolo_coco_camera.py" --camera 0 --device auto'
