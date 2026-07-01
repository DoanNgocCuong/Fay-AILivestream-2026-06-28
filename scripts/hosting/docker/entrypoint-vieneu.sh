#!/bin/bash
# =============================================================
# entrypoint-vieneu.sh -- launch VieNeu-TTS gradio wrapper
# Giong het start_vieneu() trong scripts/hosting/CKP/start.sh (da verify tao duoc audio)
# =============================================================
set -e

# Fail-fast neu GPU khong duoc nhin thay trong container -- tranh im lang
# chay tren CPU (cham gap hang chuc lan, healthcheck van "healthy" nen kho phat hien).
python3 -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" || {
    echo "[entrypoint] FATAL: GPU khong visible trong container (torch.cuda.is_available()=False)."
    echo "[entrypoint] Kiem tra: nvidia-container-toolkit da cai chua? 'docker run --gpus all' co hoat dong khong?"
    exit 1
}

# Chown volume mount (/models) cho appuser roi drop quyen root -- chi lam 1 lan
# neu ownership chua dung (bind mount tu server co the da la root tu lan chay truoc).
mkdir -p /models
if [ "$(stat -c '%U' /models)" != "appuser" ]; then
    echo "[entrypoint] Fixing ownership /models -> appuser..."
    chown -R appuser:appuser /models
fi

exec runuser -u appuser -- python3 -c "
from vieneu import Vieneu
import gradio as gr

tts = Vieneu()

def synthesize(text, voice='Bình An'):
    audio = tts.infer(text, voice=voice)
    tts.save(audio, '/tmp/out.wav')
    return '/tmp/out.wav'

app = gr.Interface(fn=synthesize, inputs=['text', 'text'], outputs='audio')
app.launch(server_name='0.0.0.0', server_port=7860, share=False)
"
