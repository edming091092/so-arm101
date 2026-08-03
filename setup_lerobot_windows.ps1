$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$VenvPath = Join-Path $RepoRoot "work\lerobot_py312"
$ScriptPath = Join-Path $RepoRoot "soarm101_collab_teleop.py"
$PatchScript = Join-Path $RepoRoot "patch_lerobot_feetech_limits.py"
$RetryPatchScript = Join-Path $RepoRoot "patch_lerobot_so101_retries.py"

function Find-Python312 {
    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            $version = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
            if ($LASTEXITCODE -eq 0 -and $version) {
                return $version.Trim()
            }
        } catch {
        }
    }

    $commonPaths = @(
        "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe",
        "$env:ProgramFiles\Python312\python.exe",
        "${env:ProgramFiles(x86)}\Python312\python.exe"
    )

    foreach ($path in $commonPaths) {
        if ($path -and (Test-Path $path)) {
            return $path
        }
    }

    return $null
}

$Python312 = Find-Python312

if (-not $Python312) {
    Write-Host "ERROR: Python 3.12 was not found." -ForegroundColor Red
    Write-Host "Install Python 3.12 from:"
    Write-Host "https://www.python.org/downloads/release/python-312/"
    Write-Host "Then run this script again."
    exit 1
}

Write-Host "Python 3.12:"
Write-Host $Python312
Write-Host ""

Write-Host "Creating LeRobot virtual environment:"
Write-Host $VenvPath
& $Python312 -m venv $VenvPath

$VenvPython = Join-Path $VenvPath "Scripts\python.exe"
$Teleop = Join-Path $VenvPath "Scripts\lerobot-teleoperate.exe"
$FindPort = Join-Path $VenvPath "Scripts\lerobot-find-port.exe"

Write-Host ""
Write-Host "Upgrading pip..."
& $VenvPython -m pip install --upgrade pip

Write-Host ""
Write-Host "Installing LeRobot with Feetech support..."
& $VenvPython -m pip install "lerobot[feetech]"

Write-Host ""
Write-Host "Checking LeRobot command line tools..."

if (Test-Path $Teleop) {
    Write-Host "OK: $Teleop" -ForegroundColor Green
} else {
    Write-Host "WARNING: lerobot-teleoperate.exe was not found. Check pip output above." -ForegroundColor Yellow
}

if (Test-Path $FindPort) {
    Write-Host "OK: $FindPort" -ForegroundColor Green
} else {
    Write-Host "WARNING: lerobot-find-port.exe was not found. Check pip output above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Applying SO-ARM101 Feetech calibration patch..."
if (Test-Path $PatchScript) {
    & $VenvPython $PatchScript
} else {
    Write-Host "WARNING: patch_lerobot_feetech_limits.py was not found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Applying SO-ARM101 serial retry patch..."
if (Test-Path $RetryPatchScript) {
    & $VenvPython $RetryPatchScript
} else {
    Write-Host "WARNING: patch_lerobot_so101_retries.py was not found." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "IMPORTANT:"
Write-Host "Each different arm set needs its own calibration id."
Write-Host "Do not reuse another arm set's calibration files."
Write-Host ""
Write-Host "Example for arm set lab01 if follower=COM4 and leader=COM5:"
Write-Host ("& `"{0}`" `"{1}`" --arm-set-id lab01 --follower-port COM4 --leader-port COM5" -f $VenvPython, $ScriptPath)
Write-Host ""
Write-Host "If the ports are reversed:"
Write-Host ("& `"{0}`" `"{1}`" --arm-set-id lab01 --follower-port COM5 --leader-port COM4" -f $VenvPython, $ScriptPath)
