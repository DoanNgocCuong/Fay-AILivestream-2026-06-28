"""
Avatar pipeline singleton — khởi động display + lắng nghe sự kiện TTS.
Gọi pipeline.start() từ fay_booter khi Fay khởi động.
Gọi pipeline.on_audio_ready(path) sau khi TTS tạo xong audio.

Streaming mode: mỗi câu TTS được submit ngay vào Wav2Lip (không chờ is_end).
Chunk đầu → play thinking phrase. Chunk cuối → play closing phrase sau khi xong.
"""
import os
import threading

from avatar import lip_sync
from avatar.video_display import get_display
from utils import util


_started = False
_lock = threading.Lock()

# Track which conversations have already submitted their first chunk
_conv_seen: set[str] = set()
_conv_lock = threading.Lock()


def start():
    global _started
    with _lock:
        if _started:
            return
        _started = True

    util.log(1, "[Avatar] Khởi động avatar pipeline...")

    from avatar import fill_phrases
    fill_phrases.precompute_async()
    util.log(1, "[Avatar] Fill phrases dang pre-compute (nen) — video display se bat dau sau khi xong...")

    # Start video display SAU KHI fill phrases san sang (chay trong thread rieng de khong block startup)
    def _delayed_start():
        ready = fill_phrases.wait_until_ready(timeout=300)
        if not ready:
            util.log(2, "[Avatar] Fill phrases timeout 300s → bat dau video display khong co fill phrases")
        else:
            util.log(1, "[Avatar] Fill phrases san sang → khoi dong video display + cho phep livestream")
        get_display().start()

    threading.Thread(target=_delayed_start, daemon=True, name="AvatarDelayedStart").start()


def on_audio_ready(
    audio_path: str,
    is_end: bool = False,
    conversation_id: str | None = None,
) -> bool:
    """Gọi từ fay_core sau khi TTS tạo xong file audio.

    Buffering mode: gom tất cả audio chunks theo conversation_id.
    Chỉ chạy Wav2Lip khi is_end=True (toàn bộ response sẵn sàng) → 1 video liền mạch.

    Returns True nếu Wav2Lip sẽ xử lý audio (caller bỏ qua audio pipeline bình thường).
    Returns False nếu Wav2Lip không khả dụng.
    """
    # audio_path rỗng + is_end=True = flush signal (không có audio mới, chỉ báo kết thúc)
    if audio_path and not os.path.exists(audio_path):
        return False
    if not audio_path and not is_end:
        return False

    from avatar import config as _cfg
    from utils import config_util as _sys_cfg

    # Ưu tiên Sync.so nếu có API key (cloud lip sync)
    syncso_key = getattr(_sys_cfg, "syncso_api_key", None)
    if syncso_key and audio_path and is_end:
        return _handle_syncso(audio_path, conversation_id)

    wav2lip_available = (
        os.path.exists(_cfg.WAV2LIP_INFERENCE)
        and os.path.exists(_cfg.WAV2LIP_CHECKPOINT)
    )
    if not wav2lip_available:
        return False

    key = conversation_id or "default"

    with _conv_lock:
        if is_end:
            _conv_seen.discard(key)

    util.log(1, f"[Pipeline] on_audio_ready: audio={'<empty>' if not audio_path else os.path.basename(audio_path)} is_end={is_end} conv={key[:8]}")
    lip_sync.submit(audio_path, is_last=is_end, conversation_id=key)
    return True


def _handle_syncso(audio_path: str, conversation_id: str | None) -> bool:
    """Gọi Sync.so trong thread riêng để không block fay_core."""
    def _run():
        try:
            from avatar import syncso_lipsync
            video_path = syncso_lipsync.generate(audio_path)
            if video_path:
                get_display().play_video(video_path)
            else:
                util.log(2, "[Pipeline] Sync.so không trả về video — bỏ qua lip sync lần này")
        except Exception as e:
            util.log(2, f"[Pipeline] Sync.so thread lỗi: {e}")

    t = threading.Thread(target=_run, daemon=True, name="SyncSoLipSync")
    t.start()
    return True  # Báo fay_core là pipeline đang xử lý


def flush_buffer(conversation_id: str | None = None):
    """No-op — streaming mode submits immediately, không có buffer để flush."""
    pass


def stop():
    get_display().stop()
    util.log(1, "[Avatar] Avatar pipeline đã dừng")
