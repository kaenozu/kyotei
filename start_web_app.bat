@echo off
echo.
echo ========================================
echo   Kyotei Web App - Starting...
echo ========================================
echo.

cd /d "%~dp0"
python scripts\web_app.py

echo.
echo ========================================
echo   Web App Stopped
echo ========================================
pause