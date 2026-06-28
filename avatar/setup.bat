@echo off
chcp 65001 >nul
echo ============================================
echo  Cai dat Avatar Lip Sync (Wav2Lip)
echo ============================================

:: 1. Cai thu vien Python
echo [1/4] Cai thu vien Python...
pip install opencv-python numpy

:: 2. Clone Wav2Lip
echo [2/4] Clone Wav2Lip...
if not exist "Wav2Lip" (
    git clone https://github.com/Rudrabha/Wav2Lip.git
) else (
    echo Wav2Lip da co san, bo qua.
)

:: 3. Cai requirement cua Wav2Lip
echo [3/4] Cai requirement Wav2Lip...
pip install -r Wav2Lip\requirements.txt

:: 4. Tai checkpoint
echo [4/4] Tai Wav2Lip checkpoint...
if not exist "Wav2Lip\checkpoints" mkdir "Wav2Lip\checkpoints"
if not exist "Wav2Lip\checkpoints\wav2lip_gan.pth" (
    echo Tai wav2lip_gan.pth tu Google Drive...
    pip install gdown -q
    python -c "import gdown; gdown.download('https://drive.google.com/uc?id=1j6SEnbTkGxRTbM7HkbCwRuVjNKI2YNH9', 'Wav2Lip/checkpoints/wav2lip_gan.pth', quiet=False)"
) else (
    echo Checkpoint da co san, bo qua.
)

echo.
echo ============================================
echo  Hoan tat! Kiem tra:
echo  - Wav2Lip/checkpoints/wav2lip_gan.pth
echo  - avatar/assets/avatar_idle.mp4 (video avatar)
echo ============================================
pause
