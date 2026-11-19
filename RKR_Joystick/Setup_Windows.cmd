@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" install_shortcuts.py
if errorlevel 1 goto failed
echo Ready. Use the two SpiRob desktop shortcuts.
pause
exit /b 0
:failed
echo Setup failed. Read the error above. Install Python 3.10+ with Tcl/Tk support.
pause
exit /b 1
