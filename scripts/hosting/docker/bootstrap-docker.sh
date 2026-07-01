#!/bin/bash
# =============================================================
# bootstrap-docker.sh -- Chay 1 lan tren GPU box moi thue.
# Cai Docker + nvidia-container-toolkit neu chua co. Idempotent.
# =============================================================
set -e

log() { echo "[$(date '+%H:%M:%S')] $1"; }

# -- Docker Engine (+ compose plugin) ----------------------------
# docker-compose-plugin khong co trong repo mac dinh Ubuntu -> dung
# script cai dat chinh thuc cua Docker (get.docker.com), bao gom
# docker-ce + compose plugin trong 1 buoc, on dinh tren moi ban Ubuntu.
if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    log "Docker + compose plugin da co san ($(docker --version)) -- bo qua"
else
    log "Cai Docker Engine (script chinh thuc get.docker.com)..."
    export DEBIAN_FRONTEND=noninteractive
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
    log "Docker installed: $(docker --version) / $(docker compose version)"
fi

# -- NVIDIA Container Toolkit ------------------------------------
if dpkg -l | grep -q nvidia-container-toolkit 2>/dev/null; then
    log "nvidia-container-toolkit da co san -- bo qua"
else
    log "Cai nvidia-container-toolkit..."
    curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey \
        | gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
    curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list \
        | sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' \
        > /etc/apt/sources.list.d/nvidia-container-toolkit.list
    apt-get update -q
    apt-get install -y -q nvidia-container-toolkit
    nvidia-ctk runtime configure --runtime=docker
    systemctl restart docker
    log "nvidia-container-toolkit installed"
fi

# -- Verify GPU visible trong container --------------------------
log "Kiem tra GPU trong container test..."
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi \
    || log "CANH BAO: GPU test container that bai -- kiem tra lai driver/toolkit truoc khi 'docker compose up'"

log "Bootstrap xong. Chay: docker compose up -d --build"
