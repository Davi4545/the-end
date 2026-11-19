@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py server\app.py
) else (
  python server\app.py
)
if errorlevel 1 pause
