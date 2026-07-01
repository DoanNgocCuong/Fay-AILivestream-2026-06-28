#!/bin/bash
# =============================================================
# stop.sh — Dừng tất cả services
# =============================================================
WORKSPACE=/workspace
VIENEU_PID="$WORKSPACE/.vieneu.pid"
MUSETALK_PID="$WORKSPACE/.musetalk.pid"

log() { echo "[$(date '+%H:%M:%S')] $1"; }

log "🛑 Dừng AI Livestream services..."

if [ -f "$VIENEU_PID" ]; then
    PID=$(cat "$VIENEU_PID")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        log "✅ VieNeu-TTS đã dừng (PID $PID)"
    else
        log "⚠️  VieNeu-TTS không chạy"
    fi
    rm -f "$VIENEU_PID"
else
    log "⚠️  VieNeu-TTS không có PID file"
fi

if [ -f "$MUSETALK_PID" ]; then
    PID=$(cat "$MUSETALK_PID")
    if kill -0 "$PID" 2>/dev/null; then
        kill "$PID"
        log "✅ MuseTalk đã dừng (PID $PID)"
    else
        log "⚠️  MuseTalk không chạy"
    fi
    rm -f "$MUSETALK_PID"
else
    log "⚠️  MuseTalk không có PID file"
fi

log "Xong."
