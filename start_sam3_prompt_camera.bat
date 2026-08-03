@echo off
cd /d "%~dp0"
if not exist "work\lerobot_py312\Scripts\python.exe" (
  echo Missing Python environment. Run setup_lerobot_windows.ps1 first.
  pause
  exit /b 1
)
set "CAMERA_ID=%~1"
set "PROMPT=%~2"
set "CONF=%~3"
set "DEVICE=%~4"
if "%CAMERA_ID%"=="" set "CAMERA_ID=0"
if "%PROMPT%"=="" set "PROMPT=cup"
if "%CONF%"=="" set "CONF=0.25"
if "%DEVICE%"=="" set "DEVICE=auto"
"work\lerobot_py312\Scripts\python.exe" "sam3_prompt_camera.py" --camera %CAMERA_ID% --prompt "%PROMPT%" --conf %CONF% --device %DEVICE%
pause
