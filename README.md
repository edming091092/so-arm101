# SO-ARM101 Collaboration Setup

This repo contains the files needed to set up a Windows computer for SO-ARM101 / SO-101 leader-follower collaboration with LeRobot.

## Files

- `setup_lerobot_windows.ps1`
  - Creates a Python 3.12 virtual environment.
  - Installs LeRobot with Feetech support.
  - Prints the command to run the collaboration script.

- `soarm101_collab_teleop.py`
  - Starts SO-ARM101 leader-to-follower teleoperation.
  - The leader arm is moved by hand.
  - The follower arm mirrors the leader arm.

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

3. Open PowerShell in this repo folder.

   If the repo is on your Desktop, you can enter the folder with:

```powershell
cd $env:USERPROFILE\Desktop\so-arm101
```

4. Run the setup script:

```powershell
powershell -ExecutionPolicy Bypass -File .\setup_lerobot_windows.ps1
```

5. Connect both SO-ARM101 arms.

6. Find the COM ports.

   You can check Windows Device Manager, or run:

```powershell
.\work\lerobot_py312\Scripts\lerobot-find-port.exe
```

7. Start collaboration.

   Example if follower is `COM4` and leader is `COM5`:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_collab_teleop.py" --follower-port COM4 --leader-port COM5
```

   If the arms are reversed, swap the ports:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_collab_teleop.py" --follower-port COM5 --leader-port COM4
```

   The script defaults to calibration ids `my_follower` and `my_leader`.
   If your calibration uses different ids, pass them explicitly:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_collab_teleop.py" --follower-port COM4 --leader-port COM5 --follower-id my_follower --leader-id my_leader
```

## Notes

- The follower arm is the robot arm that moves.
- The leader arm is the control arm you move by hand.
- Motor setup and calibration must be completed before teleoperation.
- COM ports can change between computers or USB ports.
- Keep the robot workspace clear before running motion programs.
