@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Run Setup_Windows.cmd first.
  pause
  exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" "%~dp0run_operating.py" %*
