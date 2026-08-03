# SO-ARM101 Issue Log

Date: 2026-08-03

## Goal

Prepare a small GitHub repo that can be downloaded on a new Windows computer to run SO-ARM101 / SO-101 leader-follower collaboration.

## Included Files

- `setup_lerobot_windows.ps1`
  - Creates a Python 3.12 virtual environment at `work\lerobot_py312`.
  - Installs `lerobot[feetech]`.
  - Prints the command for running teleoperation.

- `soarm101_collab_teleop.py`
  - Runs LeRobot leader-follower teleoperation.
  - Uses `so101_follower` as the robot.
  - Uses `so101_leader` as the teleoperation device.

- `README.md`
  - New-computer setup instructions.

## Problems Encountered

1. YouTube transcript was unavailable.
   - The YouTube video had transcripts disabled.
   - Workaround: used official LeRobot / SO-101 documentation for the training-flow explanation.

2. `yt-dlp` was missing on the local machine.
   - Workaround: tried `youtube-transcript-api`, but transcripts were disabled.

3. The first local file link was not openable from chat.
   - Cause: local path rendering issue.
   - Workaround: saved all user-facing files under the `outputs` folder.

4. First teleop script required ports.
   - Error: `--follower-port` and `--leader-port` were required.
   - Fix: ports are now optional. If omitted, the script asks interactively.

5. User reported current ports as `COM4` and `COM5`.
   - Unknown: which port is follower and which is leader.
   - Try follower=`COM4`, leader=`COM5` first.
   - If reversed, swap them.

6. LeRobot CLI was missing in the active Python environment.
   - Error: `lerobot-teleoperate was not found`.
   - Cause: LeRobot was not installed in that Python environment.
   - Fix: added `setup_lerobot_windows.ps1`.

7. The first PowerShell setup script failed to parse.
   - Error: `AmpersandNotAllowed`.
   - Cause: unsafe quoting in PowerShell strings.
   - Fix: rewrote the setup script with ASCII-only output and safer formatted strings.

8. Repo copies initially contained machine-specific absolute paths.
   - Fix: setup script now uses the folder where the script is located.

9. Repo copies initially had garbled non-ASCII text.
   - Fix: executable scripts and issue log were rewritten as ASCII-only files.

## Remaining Hardware Requirements

- Python 3.12 must be installed on each new computer.
- Motor setup must already be completed.
- Arm calibration must already be completed.
- Follower and leader COM ports must be identified on each computer.
- The robot workspace must be clear before motion.
