@echo off
setlocal
cd /d "%~dp0"

echo === JARVIES AI local setup ===
where py >nul 2>nul
if errorlevel 1 (
  echo Python was not found. Install Python 3.11+ and try again.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Dependency installation failed.
  pause
  exit /b 1
)

if not exist ".env" copy ".env.example" ".env" >nul

echo.
echo Setup complete.
echo Make sure Ollama is installed and run:
echo   ollama pull llama3.2:3b
echo Optional screen vision model:
echo   ollama pull llama3.2-vision:11b
echo.
echo Start JARVIES with run_jarvies.bat
pause
