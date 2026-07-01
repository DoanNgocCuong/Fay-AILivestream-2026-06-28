#!/bin/bash
# =============================================================
# entrypoint-musetalk.sh -- tai model weights (idempotent) roi launch app.py
# =============================================================
set -e

cd /workspace/MuseTalk
MODELS_DIR=/workspace/MuseTalk/models
DOWNLOAD_DIR="$MODELS_DIR/musetalk"

# Fail-fast neu GPU khong duoc nhin thay trong container -- tranh im lang
# chay tren CPU (cham gap hang chuc lan, healthcheck van "healthy" nen kho phat hien).
python3 -c "import torch, sys; sys.exit(0 if torch.cuda.is_available() else 1)" || {
    echo "[entrypoint] FATAL: GPU khong visible trong container (torch.cuda.is_available()=False)."
    echo "[entrypoint] Kiem tra: nvidia-container-toolkit da cai chua? 'docker run --gpus all' co hoat dong khong?"
    exit 1
}

if [ ! -f "$DOWNLOAD_DIR/musetalk.json" ]; then
    echo "[entrypoint] MuseTalk weights chua co, dang tai (~5GB)..."
    python3 - <<'PYEOF'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="TMElyralab/MuseTalk",
    local_dir="models/musetalk",
    ignore_patterns=["*.git*"],
)
PYEOF

    # M-14 fix: snapshot_download dat weights vao nested path sai
    #   models/musetalk/musetalk/musetalk.json     -> phai la models/musetalk/musetalk.json
    #   models/musetalk/musetalkV15/unet.pth        -> phai la models/musetalkV15/unet.pth (sibling)
    if [ -d "$DOWNLOAD_DIR/musetalk" ]; then
        cp -rn "$DOWNLOAD_DIR/musetalk/." "$DOWNLOAD_DIR/"
        rm -rf "$DOWNLOAD_DIR/musetalk"
    fi
    if [ -d "$DOWNLOAD_DIR/musetalkV15" ]; then
        mkdir -p "$MODELS_DIR/musetalkV15"
        cp -rn "$DOWNLOAD_DIR/musetalkV15/." "$MODELS_DIR/musetalkV15/"
        rm -rf "$DOWNLOAD_DIR/musetalkV15"
    fi
    echo "[entrypoint] MuseTalk weights OK"
else
    echo "[entrypoint] MuseTalk weights da co san (volume mount) -- bo qua download"
fi

# Chown volume mount cho appuser roi drop quyen root -- chi lam khi ownership
# chua dung (bind mount tu server co the da la root tu lan chay truoc).
if [ "$(stat -c '%U' "$MODELS_DIR")" != "appuser" ]; then
    echo "[entrypoint] Fixing ownership $MODELS_DIR -> appuser..."
    chown -R appuser:appuser "$MODELS_DIR"
fi

exec runuser -u appuser -- python3 app.py --server_name 0.0.0.0 --server_port 8080
