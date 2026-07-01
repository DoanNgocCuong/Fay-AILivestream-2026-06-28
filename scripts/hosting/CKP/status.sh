#!/bin/bash
# =============================================================
# status.sh — Kiểm tra trạng thái services
# =============================================================
WORKSPACE=/workspace
VIENEU_PORT=7860
MUSETALK_PORT=8080
VIENEU_PID="$WORKSPACE/.vieneu.pid"
MUSETALK_PID="$WORKSPACE/.musetalk.pid"

check_service() {
    local name=$1
    local pid_file=$2
    local port=$3

    if [ -f "$pid_file" ] && kill -0 $(cat "$pid_file") 2>/dev/null; then
        echo "🟢 $name   RUNNING  | PID: $(cat $pid_file) | Port: $port"
    else
        echo "🔴 $name   STOPPED"
    fi
}

echo "================================================"
echo " AI Livestream — Service Status"
echo " $(date)"
echo "================================================"
echo ""
check_service "VieNeu-TTS" "$VIENEU_PID" "$VIENEU_PORT"
check_service "MuseTalk  " "$MUSETALK_PID" "$MUSETALK_PORT"
echo ""
echo "GPU:"
nvidia-smi --query-gpu=name,memory.used,memory.total,utilization.gpu \
  --format=csv,noheader,nounits 2>/dev/null \
  | awk -F',' '{printf "  %s | VRAM: %s/%s MB | GPU: %s%%\n", $1,$2,$3,$4}' \
  || echo "  nvidia-smi không khả dụng"
echo "================================================"
