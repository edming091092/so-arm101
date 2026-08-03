$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$PythonExe = Join-Path $RepoRoot "work\lerobot_py312\Scripts\python.exe"
$FindPortExe = Join-Path $RepoRoot "work\lerobot_py312\Scripts\lerobot-find-port.exe"
$SetupScript = Join-Path $RepoRoot "setup_lerobot_windows.ps1"
$TeleopScript = Join-Path $RepoRoot "soarm101_collab_teleop.py"
$PatchFeetech = Join-Path $RepoRoot "patch_lerobot_feetech_limits.py"
$PatchRetries = Join-Path $RepoRoot "patch_lerobot_so101_retries.py"
$PatchObservation = Join-Path $RepoRoot "patch_lerobot_skip_optional_observation.py"

function Add-Log {
    param([string]$Message)
    $log.AppendText(("[$(Get-Date -Format HH:mm:ss)] $Message`r`n"))
    $log.SelectionStart = $log.TextLength
    $log.ScrollToCaret()
}

function Run-Capture {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    if (-not (Test-Path $FilePath)) {
        Add-Log "Missing: $FilePath"
        return
    }

    Add-Log "Running: $FilePath $($Arguments -join ' ')"
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $FilePath
    foreach ($arg in $Arguments) {
        [void]$psi.ArgumentList.Add($arg)
    }
    $psi.WorkingDirectory = $RepoRoot
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.CreateNoWindow = $true

    $process = [System.Diagnostics.Process]::Start($psi)
    $stdout = $process.StandardOutput.ReadToEnd()
    $stderr = $process.StandardError.ReadToEnd()
    $process.WaitForExit()

    if ($stdout.Trim()) { Add-Log $stdout.Trim() }
    if ($stderr.Trim()) { Add-Log $stderr.Trim() }
    Add-Log "Exit code: $($process.ExitCode)"
}

function Start-Teleop {
    $armSet = $armSetBox.Text.Trim()
    $follower = $followerBox.Text.Trim()
    $leader = $leaderBox.Text.Trim()
    $fps = $fpsBox.Text.Trim()

    if (-not $armSet -or -not $follower -or -not $leader -or -not $fps) {
        [System.Windows.Forms.MessageBox]::Show("Enter arm set id, follower COM, leader COM, and FPS.", "Missing fields")
        return
    }

    if (-not (Test-Path $PythonExe)) {
        [System.Windows.Forms.MessageBox]::Show("Run setup first. Python environment was not found.", "Setup needed")
        return
    }

    $command = "cd `"$RepoRoot`"; & `"$PythonExe`" `"$TeleopScript`" --arm-set-id $armSet --follower-port $follower --leader-port $leader --fps $fps"
    Add-Log "Opening teleop PowerShell window..."
    Add-Log $command
    Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $command
}

$form = New-Object System.Windows.Forms.Form
$form.Text = "SO-ARM101 Teaching Control"
$form.Size = New-Object System.Drawing.Size(860, 640)
$form.StartPosition = "CenterScreen"
$form.BackColor = [System.Drawing.Color]::FromArgb(246, 247, 249)
$form.Font = New-Object System.Drawing.Font("Segoe UI", 10)

$title = New-Object System.Windows.Forms.Label
$title.Text = "SO-ARM101 Teaching Control"
$title.Font = New-Object System.Drawing.Font("Segoe UI", 18, [System.Drawing.FontStyle]::Bold)
$title.AutoSize = $true
$title.Location = New-Object System.Drawing.Point(24, 20)
$form.Controls.Add($title)

$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "Use one unique arm-set id per physical arm set. Do not share calibration across different arms."
$subtitle.AutoSize = $true
$subtitle.Location = New-Object System.Drawing.Point(27, 58)
$subtitle.ForeColor = [System.Drawing.Color]::FromArgb(70, 75, 85)
$form.Controls.Add($subtitle)

$fields = New-Object System.Windows.Forms.GroupBox
$fields.Text = "Run teleoperation"
$fields.Location = New-Object System.Drawing.Point(24, 92)
$fields.Size = New-Object System.Drawing.Size(800, 130)
$form.Controls.Add($fields)

$armSetLabel = New-Object System.Windows.Forms.Label
$armSetLabel.Text = "Arm set id"
$armSetLabel.Location = New-Object System.Drawing.Point(20, 34)
$armSetLabel.AutoSize = $true
$fields.Controls.Add($armSetLabel)

$armSetBox = New-Object System.Windows.Forms.TextBox
$armSetBox.Text = "lab01"
$armSetBox.Location = New-Object System.Drawing.Point(20, 58)
$armSetBox.Size = New-Object System.Drawing.Size(180, 28)
$fields.Controls.Add($armSetBox)

$followerLabel = New-Object System.Windows.Forms.Label
$followerLabel.Text = "Follower COM"
$followerLabel.Location = New-Object System.Drawing.Point(230, 34)
$followerLabel.AutoSize = $true
$fields.Controls.Add($followerLabel)

$followerBox = New-Object System.Windows.Forms.TextBox
$followerBox.Text = "COM5"
$followerBox.Location = New-Object System.Drawing.Point(230, 58)
$followerBox.Size = New-Object System.Drawing.Size(120, 28)
$fields.Controls.Add($followerBox)

$leaderLabel = New-Object System.Windows.Forms.Label
$leaderLabel.Text = "Leader COM"
$leaderLabel.Location = New-Object System.Drawing.Point(380, 34)
$leaderLabel.AutoSize = $true
$fields.Controls.Add($leaderLabel)

$leaderBox = New-Object System.Windows.Forms.TextBox
$leaderBox.Text = "COM4"
$leaderBox.Location = New-Object System.Drawing.Point(380, 58)
$leaderBox.Size = New-Object System.Drawing.Size(120, 28)
$fields.Controls.Add($leaderBox)

$fpsLabel = New-Object System.Windows.Forms.Label
$fpsLabel.Text = "FPS"
$fpsLabel.Location = New-Object System.Drawing.Point(530, 34)
$fpsLabel.AutoSize = $true
$fields.Controls.Add($fpsLabel)

$fpsBox = New-Object System.Windows.Forms.TextBox
$fpsBox.Text = "10"
$fpsBox.Location = New-Object System.Drawing.Point(530, 58)
$fpsBox.Size = New-Object System.Drawing.Size(60, 28)
$fields.Controls.Add($fpsBox)

$startButton = New-Object System.Windows.Forms.Button
$startButton.Text = "Start teleop"
$startButton.Location = New-Object System.Drawing.Point(610, 55)
$startButton.Size = New-Object System.Drawing.Size(120, 34)
$startButton.Add_Click({ Start-Teleop })
$fields.Controls.Add($startButton)

$swapButton = New-Object System.Windows.Forms.Button
$swapButton.Text = "Swap COM"
$swapButton.Location = New-Object System.Drawing.Point(740, 55)
$swapButton.Size = New-Object System.Drawing.Size(100, 34)
$swapButton.Add_Click({
    $tmp = $followerBox.Text
    $followerBox.Text = $leaderBox.Text
    $leaderBox.Text = $tmp
    Add-Log "Swapped follower and leader COM ports."
})
$fields.Controls.Add($swapButton)

$tools = New-Object System.Windows.Forms.GroupBox
$tools.Text = "Teaching tools"
$tools.Location = New-Object System.Drawing.Point(24, 240)
$tools.Size = New-Object System.Drawing.Size(800, 108)
$form.Controls.Add($tools)

$setupButton = New-Object System.Windows.Forms.Button
$setupButton.Text = "Run setup"
$setupButton.Location = New-Object System.Drawing.Point(20, 42)
$setupButton.Size = New-Object System.Drawing.Size(120, 34)
$setupButton.Add_Click({
    Start-Process powershell.exe -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-File", "`"$SetupScript`""
    Add-Log "Opened setup in a new PowerShell window."
})
$tools.Controls.Add($setupButton)

$portsButton = New-Object System.Windows.Forms.Button
$portsButton.Text = "Find ports"
$portsButton.Location = New-Object System.Drawing.Point(160, 42)
$portsButton.Size = New-Object System.Drawing.Size(120, 34)
$portsButton.Add_Click({ Run-Capture $FindPortExe @() })
$tools.Controls.Add($portsButton)

$patchButton = New-Object System.Windows.Forms.Button
$patchButton.Text = "Apply patches"
$patchButton.Location = New-Object System.Drawing.Point(300, 42)
$patchButton.Size = New-Object System.Drawing.Size(120, 34)
$patchButton.Add_Click({
    Run-Capture $PythonExe @($PatchFeetech)
    Run-Capture $PythonExe @($PatchRetries)
    Run-Capture $PythonExe @($PatchObservation)
})
$tools.Controls.Add($patchButton)

$readmeButton = New-Object System.Windows.Forms.Button
$readmeButton.Text = "Open README"
$readmeButton.Location = New-Object System.Drawing.Point(440, 42)
$readmeButton.Size = New-Object System.Drawing.Size(120, 34)
$readmeButton.Add_Click({ Start-Process (Join-Path $RepoRoot "README.md") })
$tools.Controls.Add($readmeButton)

$note = New-Object System.Windows.Forms.Label
$note.Text = "Calibration: first run for a new arm set may ask you to move joints. Move slowly and never force the joints."
$note.Location = New-Object System.Drawing.Point(24, 365)
$note.Size = New-Object System.Drawing.Size(800, 24)
$note.ForeColor = [System.Drawing.Color]::FromArgb(55, 65, 81)
$form.Controls.Add($note)

$log = New-Object System.Windows.Forms.TextBox
$log.Multiline = $true
$log.ReadOnly = $true
$log.ScrollBars = "Vertical"
$log.Location = New-Object System.Drawing.Point(24, 400)
$log.Size = New-Object System.Drawing.Size(800, 180)
$log.Font = New-Object System.Drawing.Font("Consolas", 9)
$log.BackColor = [System.Drawing.Color]::FromArgb(17, 24, 39)
$log.ForeColor = [System.Drawing.Color]::FromArgb(229, 231, 235)
$form.Controls.Add($log)

Add-Log "Ready."
Add-Log "Current repo: $RepoRoot"
Add-Log "Use Find ports, then Start teleop."

[void]$form.ShowDialog()
