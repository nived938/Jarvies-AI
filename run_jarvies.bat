@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo JARVIES is not installed yet.
  echo Run install.bat first.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
python jarvies.py
pause
