@echo off
cd /d "%~dp0"
where py >nul 2>&1
if %errorlevel%==0 (
  py -m server.backup
) else (
  python -m server.backup
)
pause
