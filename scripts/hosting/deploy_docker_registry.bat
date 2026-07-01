@echo off
REM =============================================================
REM deploy_docker_registry.bat -- Deploy bang cach PULL image
REM tu Docker Hub (khong build tren server). Nhanh hon nhieu vi
REM server khong phai build lai tu dau.
REM
REM Dieu kien: da chay build-and-push.bat truoc de push image len.
REM Khi thue server moi: chi sua 2 dong dau roi chay lai.
REM =============================================================

REM ── SUA 2 DONG NAY KHI DOI SERVER ─────────────────────────
SET GPU_HOST=n2.ckey.vn
SET GPU_PORT=2464
REM ────────────────────────────────────────────────────────────

SET GPU_USER=root
SET REMOTE=/workspace/hosting-docker

echo ================================================
echo  Deploy AI Livestream Stack (pull tu Docker Hub)
echo  %GPU_USER%@%GPU_HOST%:%GPU_PORT%
echo ================================================
echo.

echo [1/4] Tao thu muc tren server...
ssh -o StrictHostKeyChecking=no -p %GPU_PORT% %GPU_USER%@%GPU_HOST% "mkdir -p %REMOTE%"
if %ERRORLEVEL% neq 0 (
    echo [!] Khong ket noi duoc server. Kiem tra lai GPU_HOST va GPU_PORT.
    pause & exit /b 1
)

echo [2/4] Upload docker-compose.prod.yml + bootstrap-docker.sh...
scp -P %GPU_PORT% ^
  scripts\hosting\docker\docker-compose.prod.yml ^
  scripts\hosting\docker\bootstrap-docker.sh ^
  %GPU_USER%@%GPU_HOST%:%REMOTE%/

echo [3/4] Bootstrap Docker + nvidia-container-toolkit (idempotent)...
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% ^
  "chmod +x %REMOTE%/bootstrap-docker.sh && bash %REMOTE%/bootstrap-docker.sh"

echo [4/4] docker compose pull + up -d...
ssh -p %GPU_PORT% %GPU_USER%@%GPU_HOST% ^
  "cd %REMOTE% && cp docker-compose.prod.yml docker-compose.yml && docker compose pull && docker compose up -d"

echo.
echo ================================================
echo  XONG! Ket noi:
echo    SSH  : ssh %GPU_USER%@%GPU_HOST% -p %GPU_PORT%
echo    VieNeu-TTS : http://%GPU_HOST%:7860
echo    MuseTalk   : http://%GPU_HOST%:8080
echo.
echo  Update len version moi: chay build-and-push.bat roi chay lai script nay.
echo ================================================
pause
