#!/bin/bash
# =============================================================
# start.sh — Khởi động VieNeu-TTS + MuseTalk
# =============================================================
WORKSPACE=/workspace
VENV=/workspace/venv
VENV_MUSETALK=/workspace/venv_musetalk
VIENEU_PORT=7860
MUSETALK_PORT=8080

# M-CUDA FIX: compat shim /usr/local/cuda-12.9/compat/libcuda.so.575 (sorted first
# by ldconfig via 00-compat-*.conf) overrides real driver lib -> Error 804.
# Force real driver path.
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}
VIENEU_PID="$WORKSPACE/.vieneu.pid"
MUSETALK_PID="$WORKSPACE/.musetalk.pid"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

# ── VieNeu-TTS ───────────────────────────────────────────────
start_vieneu() {
    if [ -f "$VIENEU_PID" ] && kill -0 $(cat "$VIENEU_PID") 2>/dev/null; then
        log "⚠️  VieNeu-TTS đã đang chạy (PID $(cat $VIENEU_PID))"
        return
    fi
    log "🚀 Khởi động VieNeu-TTS tại port $VIENEU_PORT..."
    source "$VENV/bin/activate"
    # VieNeu dùng gradio web interface
    nohup python3 -c "
from vieneu import Vieneu
import gradio as gr

tts = Vieneu()

def synthesize(text, voice='Bình An'):
    audio = tts.infer(text, voice=voice)
    tts.save(audio, '/tmp/out.wav')
    return '/tmp/out.wav'

app = gr.Interface(fn=synthesize, inputs=['text','text'], outputs='audio')
app.launch(server_name='0.0.0.0', server_port=$VIENEU_PORT, share=False)
" > "$WORKSPACE/vieneu.log" 2>&1 &
    echo $! > "$VIENEU_PID"
    log "✅ VieNeu-TTS | PID: $! | http://0.0.0.0:$VIENEU_PORT"
}

# ── VieNeu REST API ──────────────────────────────────────────
start_vieneu_api() {
    if [ -f "$VIENEU_PID" ] && kill -0 $(cat "$VIENEU_PID") 2>/dev/null; then
        log "⚠️  VieNeu-TTS đã đang chạy"
        return
    fi
    log "🚀 Khởi động VieNeu-TTS API (uv run vieneu-web) tại port $VIENEU_PORT..."
    source "$VENV/bin/activate"
    cd "$WORKSPACE"
    nohup python3 -m vieneu.server --host 0.0.0.0 --port $VIENEU_PORT \
        > "$WORKSPACE/vieneu.log" 2>&1 &
    echo $! > "$VIENEU_PID"
    log "✅ VieNeu-TTS API | PID: $! | http://0.0.0.0:$VIENEU_PORT"
}

# ── MuseTalk ─────────────────────────────────────────────────
start_musetalk() {
    if [ -f "$MUSETALK_PID" ] && kill -0 $(cat "$MUSETALK_PID") 2>/dev/null; then
        log "⚠️  MuseTalk đã đang chạy (PID $(cat $MUSETALK_PID))"
        return
    fi
    if [ ! -d "$WORKSPACE/MuseTalk" ]; then
        log "❌ MuseTalk chưa được cài. Chạy install.sh trước."
        return 1
    fi
    log "🚀 Khởi động MuseTalk tại port $MUSETALK_PORT..."
    source "$VENV_MUSETALK/bin/activate"
    cd "$WORKSPACE/MuseTalk"
    nohup python3 app.py \
        --server_name 0.0.0.0 --server_port $MUSETALK_PORT \
        > "$WORKSPACE/musetalk.log" 2>&1 &
    echo $! > "$MUSETALK_PID"
    log "✅ MuseTalk | PID: $! | http://0.0.0.0:$MUSETALK_PORT"
}

# ── Main ─────────────────────────────────────────────────────
log "================================================"
log " Khởi động AI Livestream Services"
log "================================================"

start_vieneu
sleep 3
start_musetalk

SERVER_IP=$(hostname -I | awk '{print $1}')
log ""
log "🟢 Services:"
log "   VieNeu-TTS : http://$SERVER_IP:$VIENEU_PORT"
log "   MuseTalk   : http://$SERVER_IP:$MUSETALK_PORT"
log ""
log "Xem log:"
log "   tail -f $WORKSPACE/vieneu.log"
log "   tail -f $WORKSPACE/musetalk.log"
log ""
log "Dừng services:"
log "   bash $WORKSPACE/stop.sh"
