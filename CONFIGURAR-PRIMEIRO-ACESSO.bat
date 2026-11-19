@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py server\app.py setup
) else (
  python server\app.py setup
)
pause
