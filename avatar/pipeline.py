"""
Avatar pipeline singleton — khởi động display + lắng nghe sự kiện TTS.
Gọi pipeline.start() từ fay_booter khi Fay khởi động.
Gọi pipeline.on_audio_ready(path) sau khi TTS tạo xong audio.
"""
import threading
import os

from avatar import lip_sync
from avatar.video_display import get_display
from utils import util


_started = False
_lock = threading.Lock()


def start():
    global _started
    with _lock:
        if _started:
            return
        _started = True

    util.log(1, "[Avatar] Khởi động avatar pipeline...")
    display = get_display()
    display.start()
    util.log(1, "[Avatar] Video display đã sẵn sàng")


def on_audio_ready(audio_path: str) -> bool:
    """Gọi từ fay_core sau khi TTS tạo xong file audio.

    Returns True nếu Wav2Lip sẽ xử lý audio (caller nên bỏ qua
    pipeline audio bình thường để tránh phát âm thanh 2 lần).
    Returns False nếu Wav2Lip không khả dụng (caller tự phát audio).
    """
    if not audio_path or not os.path.exists(audio_path):
        return False
    from avatar import config as _cfg
    wav2lip_available = (
        os.path.exists(_cfg.WAV2LIP_INFERENCE)
        and os.path.exists(_cfg.WAV2LIP_CHECKPOINT)
    )
    if not wav2lip_available:
        return False
    lip_sync.submit(audio_path)
    return True  # Wav2Lip sẽ phát audio qua lipsync video khi gen xong


def stop():
    get_display().stop()
    util.log(1, "[Avatar] Avatar pipeline đã dừng")
