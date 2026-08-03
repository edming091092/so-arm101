@echo off
cd /d "%~dp0"
if not exist "work\lerobot_py312\Scripts\python.exe" (
  echo Missing Python environment. Run setup_lerobot_windows.ps1 first.
  pause
  exit /b 1
)
"work\lerobot_py312\Scripts\python.exe" "yolo_coco_camera.py" --camera 0
pause
