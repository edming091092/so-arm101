# SO-ARM101 Collaboration Setup

This repo sets up a Windows computer for SO-ARM101 / SO-101 leader-follower collaboration with LeRobot.

Important: every different physical arm set needs its own calibration id. Do not copy one arm set's calibration file to a different arm set.

## Files

- `setup_lerobot_windows.ps1`
  - Creates a Python 3.12 virtual environment.
  - Installs LeRobot with Feetech support.
  - Prints example commands.

- `soarm101_collab_teleop.py`
  - Starts SO-ARM101 leader-to-follower teleoperation.
  - The leader arm is moved by hand.
  - The follower arm mirrors the leader arm.
  - Requires `--arm-set-id` so different arm sets do not share calibration by accident.

- `patch_lerobot_feetech_limits.py`
  - Patches LeRobot's Feetech calibration writer so out-of-range values are clamped to `0..4095`.
  - Fixes calibration failures like `Negative values are not allowed: -163`.
  - The setup script runs this automatically.

- `soarm101_issue_log.md`
  - Running log of problems found while setting this up.

## New Computer Setup

1. Install Python 3.12.

   Download from:

   https://www.python.org/downloads/release/python-312/

2. Clone this repo to the Desktop.

```powershell
cd $env:USERPROFILE\Desktop
git clone https://github.com/edming091092/so-arm101.git
cd so-arm101
```

   If Git is not installed, download the repo ZIP from GitHub, extract it to the Desktop, then open PowerShell inside the extracted `so-arm101` folder.

3. Every time you open a new PowerShell window, enter the repo folder first.

```powershell
cd $env:USERPROFILE\Desktop\so-arm101
```

4. Run the setup script.

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_lerobot_windows.ps1
```

   The setup script also applies the Feetech calibration patch. This prevents LeRobot from crashing if first-time calibration records a range such as `-163` or `4380`.

5. Connect both SO-ARM101 arms.

6. Find the COM ports.

   You can check Windows Device Manager, or run:

```powershell
.\work\lerobot_py312\Scripts\lerobot-find-port.exe
```

7. Choose an arm-set id.

   Use a different id for every different physical arm set:

```text
lab01
lab02
classroom_arm_03
```

   The script turns `lab01` into these calibration ids:

```text
lab01_follower
lab01_leader
```

8. Start collaboration.

   Example if this arm set is `lab01`, follower is `COM4`, and leader is `COM5`:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_collab_teleop.py" --arm-set-id lab01 --follower-port COM4 --leader-port COM5
```

   If the arms are reversed, swap the ports:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_collab_teleop.py" --arm-set-id lab01 --follower-port COM5 --leader-port COM4
```

9. First run for a new arm set may ask for calibration.

   Follow the LeRobot prompts carefully.

   When it asks:

```text
Move ... to the middle of its range of motion and press ENTER
```

   Move that arm to the middle of its joint range, then press ENTER.

   When it asks to move joints through the full range:

   - Move slowly.
   - Do not force any joint.
   - Do not hit mechanical limits hard.
   - Keep hands away from the follower arm.
   - Press ENTER when done.

   If it asks whether to use an existing calibration file, press ENTER.
   Type `c` only when you intentionally want to recalibrate this exact same arm set.

## Notes

- The follower arm is the robot arm that moves.
- The leader arm is the control arm you move by hand.
- Motor setup must be completed before teleoperation.
- COM ports can change between computers or USB ports.
- Keep the robot workspace clear before running motion programs.
- Different physical arm sets must use different `--arm-set-id` values.
