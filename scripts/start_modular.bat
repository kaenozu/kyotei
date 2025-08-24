@echo off
chcp 65001 >nul
echo ==========================================
echo  競艇予想システム v4.1 - モジュール化版
echo ==========================================
echo.

if "%~1"=="" (
    echo [INFO] モジュール化版Webサーバーを起動します
    echo [INFO] URL: http://localhost:5001
    echo.
    python web_app_modular.py
) else (
    if "%~1"=="web" (
        echo [INFO] モジュール化版Webサーバーを起動します
        echo [INFO] URL: http://localhost:5001
        echo.
        python web_app_modular.py
    ) else if "%~1"=="legacy" (
        echo [INFO] レガシー版システムを起動します
        cd ..
        python start_kyotei.py web
    ) else (
        echo [ERROR] 不明なオプション: %~1
        echo.
        echo 使用方法:
        echo   start_modular.bat           # モジュール化版起動
        echo   start_modular.bat web       # モジュール化版起動
        echo   start_modular.bat legacy    # レガシー版起動
    )
)

echo.
pause