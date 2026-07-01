@echo off
REM =============================================================
REM deploy.bat — Deploy scripts lên GPU server mới & chạy install
REM
REM Khi thuê server mới: chỉ sửa 2 dòng đầu rồi chạy lại.
REM =============================================================

REM ── SỬA 2 DÒNG NÀY KHI ĐỔI SERVER ─────────────────────────
SET GPU_HOST=n2.ckey.vn
SET GPU_PORT=2464
REM ────────────────────────────────────────────────────────────

SET GPU_USER=root
SET REMOTE=/workspace/hosting

echo ================================================
echo  Deploy AI Livestream Stack
echo  %GPU_USER%@%GPU_HOST%:%GPU_PORT%
echo ================================================
echo.

echo [1/3] Tao thu muc tren server...
ssh -o StrictHostKeyChecking=no -p %GPU_PORT% %GPU_USER%@%GPU_HOST% "mkdir -p %REMOTE%"
if %ERRORLEVEL% neq 0 (
    echo [!] Khong ket noi duoc server. Kiem tra lai GPU_HOST va GPU_PORT.
    pause & exit /b 1
)

echo [2/3] Upload scripts...
scp -P %GPU_PORT% ^
  scripts\hosting\install.sh ^
  scripts\hosting\start.sh ^
  scripts\hosting\stop.sh ^
  scripts\hosting\status.sh ^
  %GPU_USER%@%GPU_HOST%:%REMOTE%/

echo [3/3] Chmod + chay install.sh...
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% ^
  "chmod +x %REMOTE%/*.sh && bash %REMOTE%/install.sh"

echo.
echo ================================================
echo  XONG! Ket noi:
echo    SSH  : ssh %GPU_USER%@%GPU_HOST% -p %GPU_PORT%
echo    Web  : http://%GPU_HOST%:1689
echo.
echo  Chay services:
echo    bash /workspace/start.sh
echo ================================================
pause
