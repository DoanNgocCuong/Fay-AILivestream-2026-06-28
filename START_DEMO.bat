@echo off
chcp 65001 >nul
echo ============================================
echo   AI LIVESTREAM DEMO - Phase 1
echo   Host: Linh - Vietnamese Sales Host
echo   DR.BEE Nhuong Ong Haircare
echo ============================================
echo.

REM Set UTF-8 encoding
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

REM Check Python
python --version 2>NUL
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python chua duoc cai dat!
    pause
    exit /b 1
)

REM Check API key in system.conf
findstr /C:"DIEN_DEEPSEEK" system.conf >NUL 2>&1
if %ERRORLEVEL% EQU 0 (
    echo [ERROR] Chua dien DeepSeek API key vao system.conf!
    echo Mo file system.conf va thay chuoi "DIEN_DEEPSEEK_API_KEY_VAO_DAY" bang key that.
    echo Dang ky tai: https://platform.deepseek.com
    echo.
    pause
    exit /b 1
)

echo [OK] Config hop le - DeepSeek + Edge-TTS
echo [INFO] Khoi dong Fay AI Livestream...
echo [INFO] Sau khi chay xong, mo browser: http://127.0.0.1:5000
echo [INFO] Vao tab Voice, chon "Hoai My (vi-nu)" de dung giong tieng Viet
echo.

python main.py start

pause
