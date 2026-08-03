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

- `soarm101_smooth_direct_teleop.py`
  - Teaching-first direct teleoperation loop.
  - Skips follower observation reads.
  - Sends follower commands only when the leader changes beyond a deadband.
  - Recommended for smoother classroom demos.

- `start_teaching_ui.bat`
  - Opens the teaching UI.
  - Use this for classroom/demo use instead of typing every command manually.

- `soarm101_teaching_ui.ps1`
  - Minimal Windows UI for setup, patching, COM-port discovery, and teleoperation launch.
  - Keeps only the teaching workflow.

- `patch_lerobot_feetech_limits.py`
  - Patches LeRobot's Feetech calibration code for SO-ARM101/SO-101.
  - Clamps position-limit values to `0..4095`.
  - Normalizes homing positions before writing `Homing_Offset`.
  - Fixes calibration failures like `Negative values are not allowed: -163` and `Magnitude 4021 exceeds 2047`.
  - The setup script runs this automatically.

- `patch_lerobot_so101_retries.py`
  - Adds retries to SO-101 leader/follower `Present_Position` reads.
  - Fixes transient serial errors like `Failed to sync read 'Present_Position' ... after 1 tries`.
  - The setup script runs this automatically.

- `patch_lerobot_skip_optional_observation.py`
  - Skips optional follower observation reads when display is off.
  - This is useful because leader-to-follower control can still send leader actions even when follower observation is unavailable.
  - The setup script runs this automatically.

- `soarm101_issue_log.md`
  - Running log of problems found while setting this up.

- `setup_yolo_coco.ps1`
  - Installs YOLO COCO camera dependencies.
  - Uses pretrained COCO models, no custom training dataset required.

- `yolo_coco_camera.py`
  - Opens a camera and detects common COCO objects in real time.
  - Shows boxes on the camera image and a detected-object list.

- `start_yolo_coco_camera.bat`
  - Starts the YOLO COCO camera demo.
  - Optional first argument sets camera id, for example `.\start_yolo_coco_camera.bat 1`.

- `setup_sam3.ps1`
  - Installs SAM3 dependencies.
  - Copies `sam3.pt` into `models\sam3.pt` when it can find the model on this computer.

- `sam3_prompt_camera.py`
  - Opens a camera and runs SAM3 prompt-based segmentation.
  - Prompt and confidence can be changed while the window is open.

- `start_sam3_prompt_camera.bat`
  - Starts the SAM3 prompt camera demo.
  - Arguments: camera id, prompt, confidence.

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

   The setup script also applies local SO-ARM101 patches. These prevent LeRobot from crashing if first-time calibration records a range such as `-163`, `4380`, or a homing offset magnitude above `2047`, add retries for transient serial read failures, and skip optional follower observation reads for faster teaching teleoperation.

5. Optional: open the teaching UI.

```powershell
.\start_teaching_ui.bat
```

6. Connect both SO-ARM101 arms.

7. Find the COM ports.

   You can check Windows Device Manager, or run:

```powershell
.\work\lerobot_py312\Scripts\lerobot-find-port.exe
```

8. Choose an arm-set id.

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

9. Start collaboration.

   Recommended smooth mode if this arm set is `lab01`, follower is `COM4`, and leader is `COM5`:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_smooth_direct_teleop.py" --arm-set-id lab01 --follower-port COM4 --leader-port COM5 --fps 20
```

   If the arms are reversed, swap the ports:

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\soarm101_smooth_direct_teleop.py" --arm-set-id lab01 --follower-port COM5 --leader-port COM4 --fps 20
```

10. First run for a new arm set may ask for calibration.

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
- Teaching mode defaults to `--fps 10`. Use low FPS first; only increase after the arm is stable.
- The wrapper keeps `disable_torque_on_disconnect=false` by default to avoid extra serial writes after a communication failure.
- Keep display/visualization off for the fastest leader-to-follower response.
- If the arm stutters while idle, use `soarm101_smooth_direct_teleop.py`; it does not spam repeated identical position commands.

## Step 2: YOLO COCO Camera

This step does not train a new model. It uses an already trained COCO YOLO model to detect common objects such as person, cup, bottle, chair, keyboard, phone, and laptop.

1. Install YOLO dependencies.

```powershell
cd $env:USERPROFILE\Desktop\so-arm101
powershell -ExecutionPolicy Bypass -File .\setup_yolo_coco.ps1
```

2. Start the camera demo.

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\yolo_coco_camera.py" --camera 0
```

   Or use the bat launcher:

```powershell
.\start_yolo_coco_camera.bat 0
.\start_yolo_coco_camera.bat 1
.\start_yolo_coco_camera.bat 2
```

3. If the wrong camera opens, try another camera number.

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\yolo_coco_camera.py" --camera 1
& ".\work\lerobot_py312\Scripts\python.exe" ".\yolo_coco_camera.py" --camera 2
```

4. Useful options.

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\yolo_coco_camera.py" --camera 0 --conf 0.45 --zh-labels
```

- `--conf` controls confidence threshold.
- `--zh-labels` shows Chinese labels in the side list.
- `--model yolo11n.pt` is the default lightweight COCO model.
- Press `Q` or close the window to stop.

## Step 3: SAM3 Prompt Camera

This step uses SAM3 prompt-based segmentation. It does not train a new model. You type a prompt such as `cup`, `bottle`, `keyboard`, or `red cup`, adjust confidence, and SAM3 segments matching objects.

1. Install SAM3 dependencies and prepare `sam3.pt`.

```powershell
cd $env:USERPROFILE\Desktop\so-arm101
powershell -ExecutionPolicy Bypass -File .\setup_sam3.ps1
```

2. Start SAM3 with a prompt.

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\sam3_prompt_camera.py" --camera 0 --prompt "cup" --conf 0.25
```

3. If the wrong camera opens, change camera id.

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\sam3_prompt_camera.py" --camera 1 --prompt "bottle" --conf 0.30
```

4. Multiple prompts are allowed.

```powershell
& ".\work\lerobot_py312\Scripts\python.exe" ".\sam3_prompt_camera.py" --camera 0 --prompt "cup, bottle, keyboard" --conf 0.25
```

5. Bat launcher examples.

```powershell
.\start_sam3_prompt_camera.bat 0 cup 0.25
.\start_sam3_prompt_camera.bat 1 bottle 0.30
```

- `Prompt` tells SAM3 what object to segment.
- `Conf` controls detection confidence. Lower values find more objects but can include mistakes.
- Press `Q` or close the window to stop.
