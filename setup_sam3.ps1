param(
    [ValidateSet("auto", "cpu", "gpu", "cuda")]
    [string]$Device = "auto"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "work\lerobot_py312\Scripts\python.exe"
$TorchSetupScript = Join-Path $RepoRoot "setup_pytorch_device.ps1"
$ModelsDir = Join-Path $RepoRoot "models"
$TargetModel = Join-Path $ModelsDir "sam3.pt"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Python environment was not found." -ForegroundColor Red
    Write-Host "Run setup_lerobot_windows.ps1 first:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\setup_lerobot_windows.ps1"
    exit 1
}

Write-Host "Installing SAM3 dependencies into:"
Write-Host $VenvPython
Write-Host ""

& $TorchSetupScript -Device $Device
& $VenvPython -m pip install --upgrade ultralytics pillow

New-Item -ItemType Directory -Force -Path $ModelsDir | Out-Null

if (Test-Path $TargetModel) {
    Write-Host "OK: SAM3 model already exists:"
    Write-Host $TargetModel
} else {
    $Candidates = @(
        "$env:USERPROFILE\Desktop\sam3.pt",
        "$env:USERPROFILE\Downloads\sam3.pt",
        "C:\Users\USER\Documents\Codex\2026-06-09\so-arm101-ai-pro\dist\SO101Lab_Offline_Internal_2026.07.22\payload\models\sam3.pt"
    )

    $SourceModel = $null
    foreach ($candidate in $Candidates) {
        if (Test-Path $candidate) {
            $SourceModel = $candidate
            break
        }
    }

    if ($SourceModel) {
        Write-Host "Copying SAM3 model:"
        Write-Host $SourceModel
        Copy-Item -LiteralPath $SourceModel -Destination $TargetModel -Force
        Write-Host "OK: copied to:"
        Write-Host $TargetModel
    } else {
        Write-Host "WARNING: sam3.pt was not found." -ForegroundColor Yellow
        Write-Host "Put sam3.pt here, then run this script again:"
        Write-Host $TargetModel
    }
}

Write-Host ""
Write-Host "SAM3 setup complete."
Write-Host "Run:"
Write-Host '& ".\work\lerobot_py312\Scripts\python.exe" ".\sam3_prompt_camera.py" --camera 0 --prompt "cup" --conf 0.25 --device auto'
