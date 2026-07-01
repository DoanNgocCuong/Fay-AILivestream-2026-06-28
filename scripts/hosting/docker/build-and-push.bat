@echo off
REM =============================================================
REM build-and-push.bat -- Build 2 image tren may local roi push
REM len Docker Hub (doanngoccuong/fay-vieneu-tts, fay-musetalk).
REM
REM Chay tu thu muc goc repo. Can "docker login" truoc (1 lan).
REM =============================================================

SET DOCKERHUB_USER=doanngoccuong

REM Tag theo git short-sha de rollback duoc (khong chi de :latest -- neu build
REM moi loi, server van co the pull lai tag cu cu the thay vi mat ban chay tot).
FOR /F %%i IN ('git rev-parse --short HEAD') DO SET GIT_SHA=%%i
SET TAG=%GIT_SHA%

echo ================================================
echo  Build + Push AI Livestream images -> Docker Hub
echo  %DOCKERHUB_USER%  (tag: %TAG% + latest)
echo ================================================
echo.

echo [0/5] Kiem tra dang nhap Docker Hub...
docker info | findstr /C:"Username" >nul
if %ERRORLEVEL% neq 0 (
    echo [!] Chua dang nhap Docker Hub. Chay: docker login
    pause & exit /b 1
)

echo [1/5] Build vieneu-tts...
docker build -f scripts\hosting\docker\Dockerfile.vieneu -t %DOCKERHUB_USER%/fay-vieneu-tts:%TAG% -t %DOCKERHUB_USER%/fay-vieneu-tts:latest scripts\hosting\docker
if %ERRORLEVEL% neq 0 (echo [!] Build vieneu-tts that bai & pause & exit /b 1)

echo [2/5] Build musetalk...
docker build -f scripts\hosting\docker\Dockerfile.musetalk -t %DOCKERHUB_USER%/fay-musetalk:%TAG% -t %DOCKERHUB_USER%/fay-musetalk:latest scripts\hosting\docker
if %ERRORLEVEL% neq 0 (echo [!] Build musetalk that bai & pause & exit /b 1)

echo [3/5] Push vieneu-tts (%TAG% + latest)...
docker push %DOCKERHUB_USER%/fay-vieneu-tts:%TAG%
docker push %DOCKERHUB_USER%/fay-vieneu-tts:latest
if %ERRORLEVEL% neq 0 (echo [!] Push vieneu-tts that bai & pause & exit /b 1)

echo [4/5] Push musetalk (%TAG% + latest)...
docker push %DOCKERHUB_USER%/fay-musetalk:%TAG%
docker push %DOCKERHUB_USER%/fay-musetalk:latest
if %ERRORLEVEL% neq 0 (echo [!] Push musetalk that bai & pause & exit /b 1)

echo [5/5] Xong.
echo.
echo ================================================
echo  Images da len Docker Hub (tag %TAG% + latest):
echo    https://hub.docker.com/r/%DOCKERHUB_USER%/fay-vieneu-tts
echo    https://hub.docker.com/r/%DOCKERHUB_USER%/fay-musetalk
echo.
echo  Deploy len GPU server: chay deploy_docker_registry.bat
echo  Rollback: sua IMAGE_TAG trong docker-compose.prod.yml ve tag cu, roi
echo            docker compose pull ^&^& docker compose up -d tren server.
echo ================================================
pause
