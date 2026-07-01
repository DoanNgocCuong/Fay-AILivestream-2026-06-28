#!/bin/bash
# =============================================================
# install.sh -- Cai toan bo AI Livestream stack tren GPU server
#
# Stack: VieNeu-TTS v3 Turbo + MuseTalk
# Yeu cau: Ubuntu 20.04/22.04/24.04 + CUDA 12.x
# Idempotent: chay lai nhieu lan khong bi loi.
# =============================================================
WORKSPACE=/workspace
VENV="$WORKSPACE/venv"
LOG="$WORKSPACE/install.log"
CHECKPOINT="$WORKSPACE/.install_checkpoint"
mkdir -p "$WORKSPACE"

log()       { echo "[$(date '+%H:%M:%S')] $1" | tee -a "$LOG"; }
mark_done() { echo "STEP_$1=done" >> "$CHECKPOINT"; log "STEP $1 done"; }
skip()      { log "STEP $1 da xong (checkpoint) -- bo qua"; }
need()      { ! grep -q "STEP_$1=done" "$CHECKPOINT" 2>/dev/null; }

log "================================================"
log " AI Livestream -- GPU Install Script"
log " $(date)"
log "================================================"

# -- STEP 1: Kiem tra GPU -------------------------------------
if need 1; then
  log ""
  log "[STEP 1] Kiem tra GPU & CUDA..."
  nvidia-smi --query-gpu=name,memory.total,driver_version \
    --format=csv,noheader | tee -a "$LOG"
  mark_done 1
else skip 1; fi

# -- STEP 2: System packages ----------------------------------
if need 2; then
  log ""
  log "[STEP 2] Cai system packages..."
  export DEBIAN_FRONTEND=noninteractive
  ln -sf /usr/share/zoneinfo/Asia/Ho_Chi_Minh /etc/localtime
  echo "Asia/Ho_Chi_Minh" > /etc/timezone
  apt-get update -q
  apt-get install -y -q \
    git ffmpeg wget curl unzip \
    python3-pip python3-venv \
    libsndfile1 libportaudio2 \
    build-essential dos2unix
  mark_done 2
else skip 2; fi

# -- STEP 3: Virtual environment ------------------------------
if need 3; then
  log ""
  log "[STEP 3] Tao Python venv tai $VENV..."
  python3 -m venv "$VENV"
  source "$VENV/bin/activate"
  pip install --upgrade pip -q
  mark_done 3
else
  skip 3
  source "$VENV/bin/activate"
fi

# -- STEP 4: PyTorch CUDA -------------------------------------
if need 4; then
  log ""
  log "[STEP 4] Cai PyTorch 2.5.1 (cu121 - compatible voi CUDA 12.x driver)..."
  # Dung cu121 thay vi cu128/cu130: driver host khong forward-compat (Error 804)
  # torch 2.1.2 khong con tren PyPI index (archived) -- dung 2.5.1 (cu121, da verify)
  pip install \
    "torch==2.5.1" torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121 -q
  LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu python3 - <<'PYEOF'
import torch
if torch.cuda.is_available():
    print("PyTorch " + str(torch.__version__) + " | GPU: " + torch.cuda.get_device_name(0))
else:
    print("WARNING: CUDA not available - check driver/LD_LIBRARY_PATH. torch version: " + str(torch.__version__))
PYEOF
  mark_done 4
else skip 4; fi

# -- STEP 5: VieNeu-TTS ---------------------------------------
if need 5; then
  log ""
  log "[STEP 5] Cai VieNeu-TTS..."
  # KHONG co lmdeploy (conflict voi torch 2.x)
  pip install \
    "transformers" \
    "librosa>=0.11.0" \
    "neucodec>=0.0.4" \
    "sea-g2p>=0.7.14" \
    "onnxruntime-gpu" \
    "gradio>=5.49.1" \
    "huggingface_hub" \
    "perth>=0.2.0" \
    "soundfile" "soxr" "numpy" "PyYAML" \
    -q
  pip install "vieneu" -q
  # M-24 FIX: "vieneu" keo theo torch moi hon lam dependency (khong dung
  # --no-deps), ghi de pin cu121 tu STEP 4 -> torch cu130+ khong tuong
  # thich driver <570 (Error: CUDA not available). Re-pin lai torch sau
  # khi cai vieneu de dam bao dung ban cu121 da verify.
  pip install \
    "torch==2.5.1" torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu121 -q
  LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu python3 - <<'PYEOF'
from vieneu import Vieneu
import torch
if not torch.cuda.is_available():
    raise SystemExit("WARNING: CUDA not available sau khi re-pin torch - kiem tra driver/LD_LIBRARY_PATH. torch version: " + str(torch.__version__))
tts = Vieneu()
voices = tts.list_preset_voices()
print("VieNeu-TTS OK -- " + str(len(voices)) + " voices loaded | torch " + str(torch.__version__) + " | GPU: " + torch.cuda.get_device_name(0))
PYEOF
  mark_done 5
else skip 5; fi

# -- STEP 6: VieNeu test audio --------------------------------
if need 6; then
  log ""
  log "[STEP 6] Test VieNeu generate audio..."
  python3 - <<'PYEOF'
from vieneu import Vieneu
tts = Vieneu()
audio = tts.infer('Xin chao, day la test VieNeu TTS.')
tts.save(audio, '/tmp/test_vieneu.wav')
print("Audio OK -> /tmp/test_vieneu.wav")
PYEOF
  mark_done 6
else skip 6; fi

# -- STEP 7: MuseTalk -----------------------------------------
if need 7; then
  log ""
  log "[STEP 7] Clone MuseTalk..."
  cd "$WORKSPACE"
  if [ ! -d "MuseTalk" ]; then
    git clone https://github.com/TMElyralab/MuseTalk.git
  fi
  cd "$WORKSPACE/MuseTalk"
  pip install -r requirements.txt -q
  mark_done 7
else skip 7; fi

# -- STEP 8: MuseTalk weights ---------------------------------
if need 8; then
  log ""
  log "[STEP 8] Tai MuseTalk model weights (~5GB)..."
  cd "$WORKSPACE/MuseTalk"
  python3 - <<'PYEOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='TMElyralab/MuseTalk',
    local_dir='models/musetalk',
    ignore_patterns=['*.git*']
)
print("MuseTalk weights OK")
PYEOF
  mark_done 8
else skip 8; fi

# -- STEP 9: Copy service scripts -----------------------------
if need 9; then
  log ""
  log "[STEP 9] Cai service scripts..."
  SCRIPT_DIR="$(dirname "$0")"
  for f in start.sh stop.sh status.sh; do
    cp "$SCRIPT_DIR/$f" "$WORKSPACE/$f"
    chmod +x "$WORKSPACE/$f"
  done
  sed -i "s|VENV=.*|VENV=$VENV|g" "$WORKSPACE/start.sh"
  mark_done 9
else skip 9; fi

# -- Tom tat --------------------------------------------------
log ""
log "================================================"
log " CAI DAT HOAN TAT"
log "================================================"
log ""
log " Chay services:    bash $WORKSPACE/start.sh"
log " Kiem tra:         bash $WORKSPACE/status.sh"
log " Log:              $LOG"
