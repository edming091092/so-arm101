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

10. GitHub push is using the wrong cached credential.
   - Push error: `Permission to edming091092/so-arm101.git denied to Ununvailable.`
   - Cause: Git Credential Manager is using a cached GitHub identity named `Ununvailable`, even if the browser is logged into another account.
   - Incorrect cleanup command tried: `git credential-manager erase https://github.com`
   - Result: `Unrecognized command or argument 'https://github.com'.`
   - Correct cleanup approach: pipe a credential record into `git credential-manager erase`, or remove the GitHub entry from Windows Credential Manager.

11. Teleoperation found LeRobot but leader calibration failed with a negative limit.
   - Error: `ValueError: Negative values are not allowed: -165`
   - Context: the script used default ids `my_awesome_follower_arm` and `my_awesome_leader_arm`.
   - Local calibration files already existed as `my_follower.json` and `my_leader.json`.
   - Likely cause: LeRobot could not find calibration files for the `my_awesome_*` ids, so it started a fresh calibration and computed an invalid negative motor position limit.
   - Fix: default calibration ids changed to `my_follower` and `my_leader`.

12. Bundling calibration files was the wrong approach for different arm sets.
   - Problem: calibration files are hardware-specific.
   - Risk: copying `my_follower.json` and `my_leader.json` to a different physical arm set can cause bad motion or calibration mismatch.
   - Fix: remove bundled calibration as the default solution.
   - Fix: require `--arm-set-id` so every physical arm set gets separate ids such as `lab01_follower` and `lab01_leader`.
   - Fix: README now explains first-run calibration for each new arm set.

13. First calibration for a different arm set still failed with out-of-range Feetech limits.
   - Error: `ValueError: Negative values are not allowed: -163`
   - Observed table included `elbow_flex MIN -163` and `wrist_flex MAX 4380`.
   - Cause: LeRobot writes recorded SO leader/follower range limits directly to Feetech position-limit registers, but Feetech limits must be in `0..4095`.
   - Fix: added `patch_lerobot_feetech_limits.py`.
   - Fix: setup script now applies the patch automatically after installing LeRobot.

14. First calibration also failed while writing Feetech homing offsets.
   - Error: `ValueError: Magnitude 4021 exceeds 2047 (max for sign_bit_index=11)`.
   - Cause: LeRobot computed `Homing_Offset = Present_Position - 2047`, but some Feetech raw positions can be outside a single 0..4095 turn during calibration.
   - Fix: updated `patch_lerobot_feetech_limits.py` to normalize homing positions modulo 4096 before computing the offset, then clamp the offset to the writable range.

15. Teleoperation reached the 60 Hz loop but follower sync read failed.
   - Error: `Failed to sync read 'Present_Position' on ids=[1, 2, 3, 4, 5, 6] after 1 tries`.
   - Cause: LeRobot SO-101 follower/leader reads use `num_retry=0`, so a single transient Feetech serial failure ends teleoperation.
   - Fix: added `patch_lerobot_so101_retries.py`.
   - Fix: setup script now applies the retry patch automatically.

16. Teaching workflow should not require typing every command.
   - Request: keep only the UI features needed for teaching.
   - Fix: added `start_teaching_ui.bat` and `soarm101_teaching_ui.ps1`.
   - UI includes setup, patching, COM-port discovery, COM swap, README access, and teleoperation launch.

17. Teleoperation still failed at default 60 FPS even with retries.
   - Log: `Teleop loop time: 52.11ms (19 Hz)`.
   - Error: `Failed to sync read 'Present_Position' ... after 6 tries. [TxRxResult] There is no status packet!`
   - Follow-up error during disconnect: failed to write `Torque_Enable=0` after 6 tries.
   - Cause: default 60 FPS overloaded the SO-101 Feetech serial bus on this setup, and disconnect tried another serial write after communication was already unhealthy.
   - Fix: wrapper now defaults to `--fps 10`.
   - Fix: wrapper now sets `--robot.disable_torque_on_disconnect=false` by default.

18. Teleoperation still failed at 10 FPS because follower observation read failed.
   - Error: `Failed to sync read 'Present_Position' ... after 6 tries. [TxRxResult] There is no status packet!`
   - Context: LeRobot teleop loop reads follower observation before leader action, but its own comment says the observation is not really needed unless visualization/processors use it.
   - Fix: added `patch_lerobot_skip_optional_observation.py`.
   - Fix: setup script now applies the optional-observation patch automatically.

19. Teleoperation felt like only about 3 Hz after the optional-observation warning patch.
   - Cause: the first observation patch still attempted follower sync reads every loop, then waited through retries before continuing.
   - Fix: updated `patch_lerobot_skip_optional_observation.py` to skip follower observation entirely when `display_data=false`.
   - Expected result: teaching teleop loop becomes leader read plus follower write, avoiding the slow failing follower read path.

20. Motion still felt jerky and pulsed while idle.
   - Likely cause: the generic LeRobot teleop loop still sends repeated follower goal-position writes even when the leader has not moved.
   - Fix: added `soarm101_smooth_direct_teleop.py`.
   - Fix: teaching UI now launches the smooth direct teleop script.
   - Behavior: smooth direct teleop skips follower observation reads and writes to follower only when leader motion exceeds a deadband.

21. Step 2 requested: YOLO COCO camera detection without custom training.
   - Goal: use an already trained COCO model to detect general objects from a camera.
   - Fix: added `setup_yolo_coco.ps1`.
   - Fix: added `yolo_coco_camera.py`.
   - Fix: added `start_yolo_coco_camera.bat`.
   - Fix: teaching UI now includes a `YOLO COCO` button.

22. YOLO camera id must be editable.
   - Fix: teaching UI now has a `Cam` field used by the `YOLO COCO` button.
   - Fix: `start_yolo_coco_camera.bat` now accepts an optional camera id argument.

23. Step 3 requested: SAM3 prompt segmentation.
   - Goal: add SAM3 recognition/segmentation with editable prompt and confidence.
   - Fix: added `setup_sam3.ps1`.
   - Fix: added `sam3_prompt_camera.py`.
   - Fix: added `start_sam3_prompt_camera.bat`.
   - Fix: teaching UI now includes SAM3 prompt, confidence, and launch controls.

## Remaining Hardware Requirements

- Python 3.12 must be installed on each new computer.
- Motor setup must already be completed.
- Arm calibration must already be completed.
- Follower and leader COM ports must be identified on each computer.
- The robot workspace must be clear before motion.
