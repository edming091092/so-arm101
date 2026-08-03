param(
    [ValidateSet("auto", "cpu", "gpu", "cuda")]
    [string]$Device = "auto"
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPython = Join-Path $RepoRoot "work\lerobot_py312\Scripts\python.exe"

if (-not (Test-Path $VenvPython)) {
    Write-Host "ERROR: Python environment was not found." -ForegroundColor Red
    Write-Host "Run setup_lerobot_windows.ps1 first:"
    Write-Host "powershell -ExecutionPolicy Bypass -File .\setup_lerobot_windows.ps1"
    exit 1
}

function Test-NvidiaGpu {
    $nvidia = Get-Command nvidia-smi -ErrorAction SilentlyContinue
    if (-not $nvidia) {
        return $false
    }

    & nvidia-smi | Out-Null
    return ($LASTEXITCODE -eq 0)
}

$RequestedDevice = $Device.ToLowerInvariant()
if ($RequestedDevice -eq "gpu") {
    $RequestedDevice = "cuda"
}

if ($RequestedDevice -eq "auto") {
    if (Test-NvidiaGpu) {
        $RequestedDevice = "cuda"
    } else {
        $RequestedDevice = "cpu"
    }
}

Write-Host "Preparing PyTorch runtime:" $RequestedDevice

$CheckScript = @"
import sys
try:
    import torch
except Exception:
    sys.exit(10)
want = sys.argv[1]
has_cuda = torch.cuda.is_available()
if want == 'cuda' and has_cuda:
    print('PyTorch CUDA is already ready:', torch.__version__, torch.cuda.get_device_name(0))
    sys.exit(0)
if want == 'cpu' and not has_cuda:
    print('PyTorch CPU is already ready:', torch.__version__)
    sys.exit(0)
sys.exit(20)
"@

& $VenvPython -c $CheckScript $RequestedDevice
if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "PyTorch runtime setup complete."
    exit 0
}

if ($RequestedDevice -eq "cuda") {
    if (-not (Test-NvidiaGpu)) {
        Write-Host "ERROR: NVIDIA GPU/driver was not detected by nvidia-smi." -ForegroundColor Red
        Write-Host "Install or update the NVIDIA driver first, then run this again."
        exit 1
    }

    Write-Host "Installing CUDA PyTorch wheels. This download can be large."
    & $VenvPython -m pip install --upgrade --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cu128
} else {
    Write-Host "Installing CPU PyTorch wheels."
    & $VenvPython -m pip install --upgrade --force-reinstall torch torchvision --index-url https://download.pytorch.org/whl/cpu
}

Write-Host ""
Write-Host "Verifying PyTorch runtime..."
& $VenvPython -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_version', torch.version.cuda); print('device_name', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU only')"

Write-Host ""
Write-Host "PyTorch runtime setup complete."
