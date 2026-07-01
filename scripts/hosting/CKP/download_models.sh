#!/bin/bash
# Download all MuseTalk model weights using new `hf` CLI
set -e
cd /workspace/MuseTalk

source /workspace/venv_musetalk/bin/activate

echo "[1/6] Fix musetalk paths (move from nested dir)..."
mkdir -p models/musetalk models/musetalkV15 models/syncnet models/dwpose models/face-parse-bisent models/sd-vae models/whisper

# Fix: snapshot_download put files in models/musetalk/musetalk/ -> move to models/musetalk/
if [ -f "models/musetalk/musetalk/musetalk.json" ]; then
  cp models/musetalk/musetalk/* models/musetalk/ 2>/dev/null || true
  echo "  Fixed musetalk v1 path"
fi
if [ -f "models/musetalk/musetalkV15/unet.pth" ]; then
  cp models/musetalk/musetalkV15/* models/musetalkV15/ 2>/dev/null || true
  echo "  Fixed musetalk v1.5 path"
fi

echo "[2/6] Download SD VAE..."
hf download stabilityai/sd-vae-ft-mse \
  --include "config.json" "diffusion_pytorch_model.bin" \
  --local-dir models/sd-vae

echo "[3/6] Download Whisper tiny..."
hf download openai/whisper-tiny \
  --include "config.json" "pytorch_model.bin" "preprocessor_config.json" \
  --local-dir models/whisper

echo "[4/6] Download DWPose..."
hf download yzd-v/DWPose \
  --include "dw-ll_ucoco_384.pth" \
  --local-dir models/dwpose

echo "[5/6] Download SyncNet..."
hf download ByteDance/MuseTalk \
  --include "syncnet*" \
  --local-dir models/syncnet 2>/dev/null || \
hf download TMElyralab/MuseTalk \
  --include "syncnet*" \
  --local-dir models/syncnet 2>/dev/null || \
echo "  SyncNet: will try alternative..."

echo "[6/6] Download face-parse model..."
hf download jonathandinu/face-parsing \
  --include "*.pth" "*.json" \
  --local-dir models/face-parse-bisent 2>/dev/null || \
echo "  face-parse: using existing resnet18"

echo ""
echo "=== Models downloaded ==="
find models -type f -name "*.pth" -o -name "*.bin" -o -name "*.json" | grep -v cache | sort
