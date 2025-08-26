@echo off
echo ===================================================
echo   競艇予想システム起動中...
echo ===================================================
echo.

cd /d "%~dp0"
echo 現在のディレクトリ: %CD%
echo.

echo システム起動中...
python openapi_app.py

echo.
echo システムが停止しました。
pause