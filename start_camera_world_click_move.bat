@echo off
cd /d "%~dp0"
if not exist "work\lerobot_py312\Scripts\python.exe" (
  echo Missing Python environment. Run setup_lerobot_windows.ps1 first.
  pause
  exit /b 1
)
set "ARM_SET=%~1"
set "FOLLOWER=%~2"
set "LEADER=%~3"
set "CAMERA_ID=%~4"
if "%ARM_SET%"=="" set "ARM_SET=lab01"
if "%FOLLOWER%"=="" set "FOLLOWER=COM5"
if "%LEADER%"=="" set "LEADER=COM4"
if "%CAMERA_ID%"=="" set "CAMERA_ID=0"
"work\lerobot_py312\Scripts\python.exe" "camera_world_click_move.py" --arm-set-id "%ARM_SET%" --follower-port "%FOLLOWER%" --leader-port "%LEADER%" --camera %CAMERA_ID%
pause
