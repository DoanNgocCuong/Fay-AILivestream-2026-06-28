@echo off
REM =============================================================
REM deploy_docker.bat — Deploy VieNeu-TTS + MuseTalk qua Docker Compose
REM
REM Khi thue server moi: chi sua 2 dong dau roi chay lai.
REM =============================================================

REM ── SUA 2 DONG NAY KHI DOI SERVER ─────────────────────────
SET GPU_HOST=n2.ckey.vn
SET GPU_PORT=2464
REM ────────────────────────────────────────────────────────────

SET GPU_USER=root
SET REMOTE=/workspace/hosting-docker

echo ================================================
echo  Deploy AI Livestream Stack (Docker Compose)
echo  %GPU_USER%@%GPU_HOST%:%GPU_PORT%
echo ================================================
echo.

echo [1/4] Tao thu muc tren server...
ssh -o StrictHostKeyChecking=no -p %GPU_PORT% %GPU_USER%@%GPU_HOST% "mkdir -p %REMOTE%"
if %ERRORLEVEL% neq 0 (
    echo [!] Khong ket noi duoc server. Kiem tra lai GPU_HOST va GPU_PORT.
    pause & exit /b 1
)

echo [2/4] Upload thu muc docker/...
scp -r -P %GPU_PORT% ^
  scripts\hosting\docker\. ^
  %GPU_USER%@%GPU_HOST%:%REMOTE%/

echo [3/4] Bootstrap Docker + nvidia-container-toolkit (idempotent)...
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% ^
  "chmod +x %REMOTE%/*.sh && bash %REMOTE%/bootstrap-docker.sh"

echo [4/4] docker compose up -d --build...
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% ^
  "cd %REMOTE% && docker compose up -d --build"

echo.
echo ================================================
echo  XONG! Ket noi:
echo    SSH  : ssh %GPU_USER%@%GPU_HOST% -p %GPU_PORT%
echo    VieNeu-TTS : http://%GPU_HOST%:7860
echo    MuseTalk   : http://%GPU_HOST%:8080
echo.
echo  Kiem tra trang thai:
echo    ssh %GPU_USER%@%GPU_HOST% -p %GPU_PORT% "cd %REMOTE% && docker compose ps"
echo ================================================
pause
