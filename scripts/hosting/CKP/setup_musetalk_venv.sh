#!/bin/bash
# Setup separate venv for MuseTalk to avoid conflicts with VieNeu
set -e
VENV=/workspace/venv_musetalk

echo "[1/3] Creating MuseTalk venv (Python 3.11 -- mmcv khong co wheel cp312)..."
python3.11 -m venv $VENV
source $VENV/bin/activate
pip install --upgrade pip -q

echo "[2/3] Installing PyTorch cu121..."
pip install torch==2.5.1 torchvision torchaudio \
  --index-url https://download.pytorch.org/whl/cu121 -q

echo "[3/5] Installing MuseTalk deps..."
pip install \
  "opencv-python==4.9.0.80" \
  "diffusers==0.30.2" \
  "accelerate==0.28.0" \
  "transformers==4.39.2" \
  "huggingface_hub==0.30.2" \
  "numpy==1.26.4" \
  "soundfile==0.12.1" \
  "librosa==0.11.0" \
  "einops==0.8.1" \
  "omegaconf" \
  "ffmpeg-python" \
  "moviepy<2" \
  "imageio[ffmpeg]" \
  "gdown" \
  "requests" \
  "gradio" \
  -q

# M-18 FIX: setuptools 68.2.2 la sweet spot -- 71.x+ bo pkg_resources
# khoi site-packages, 82.x khong con pkg_resources -- ca 2 deu lam mmcv fail.
echo "[4/5] Installing mmpose (setuptools==68.2.2 pin)..."
pip install "setuptools==68.2.2" wheel -q
pip install mmengine -q
pip install "mmcv==2.1.0" --no-build-isolation \
  -f https://download.openmmlab.com/mmcv/dist/cu121/torch2.5.1/index.html -q

# M-19 FIX: xtcocotools sdist thieu _mask.c, khong build duoc -- shim sang pycocotools
pip install pycocotools -q
SITE_PKG=$($VENV/bin/python -c "import site; print(site.getsitepackages()[0])")
mkdir -p "$SITE_PKG/xtcocotools"
cat > "$SITE_PKG/xtcocotools/__init__.py" <<'PYEOF'
from pycocotools import *
PYEOF
mkdir -p "$SITE_PKG/xtcocotools-1.14.3.dist-info"
printf 'Metadata-Version: 2.1\nName: xtcocotools\nVersion: 1.14.3\n' > "$SITE_PKG/xtcocotools-1.14.3.dist-info/METADATA"
echo "xtcocotools" > "$SITE_PKG/xtcocotools-1.14.3.dist-info/top_level.txt"

pip install mmpose mmdet -q
pip install face-alignment -q

# M-23 FIX: mmpose/mmdet keo tifffile yeu cau numpy>=2.1, tu upgrade pha cv2
pip install "numpy==1.26.4" -q

echo "[5/5] Verifying install..."
echo "VENV_MUSETALK_DONE"
python3 -c "
import cv2, torch, transformers
from mmpose.apis import inference_topdown
print('cv2:', cv2.__version__)
print('torch:', torch.__version__)
print('transformers:', transformers.__version__)
print('mmpose: OK')
print('ALL OK')
"
