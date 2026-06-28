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


def on_audio_ready(audio_path: str):
    """Gọi từ fay_core sau khi TTS tạo xong file audio."""
    if not audio_path or not os.path.exists(audio_path):
        return
    lip_sync.submit(audio_path)


def stop():
    get_display().stop()
    util.log(1, "[Avatar] Avatar pipeline đã dừng")
