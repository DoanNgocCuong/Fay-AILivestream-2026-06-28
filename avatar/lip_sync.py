"""
Wav2Lip processor — chạy inference async, không block TTS pipeline.
Queue: audio_path → Wav2Lip → lipsync video → VideoDisplay.play_lipsync()
"""
import os
import queue
import subprocess
import sys
import threading
import time

from avatar import config
from utils import util


_job_queue: queue.Queue = queue.Queue()
_worker_thread: threading.Thread | None = None
_started = False
_lock = threading.Lock()


def submit(audio_path: str):
    """Đưa audio vào queue để xử lý lip sync async."""
    if not _is_wav2lip_available():
        util.log(2, "[LipSync] Wav2Lip chưa cài, bỏ qua lip sync. Xem avatar/README.md")
        return
    _ensure_started()
    _job_queue.put(audio_path)


def _is_wav2lip_available() -> bool:
    return (
        os.path.exists(config.WAV2LIP_INFERENCE)
        and os.path.exists(config.WAV2LIP_CHECKPOINT)
    )


def _get_face_input() -> str | None:
    if os.path.exists(config.AVATAR_VIDEO_PATH):
        return config.AVATAR_VIDEO_PATH
    if os.path.exists(config.AVATAR_IMAGE_PATH):
        return config.AVATAR_IMAGE_PATH
    return None


def _ensure_started():
    global _worker_thread, _started
    with _lock:
        if not _started:
            _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
            _worker_thread.start()
            _started = True


def _worker_loop():
    from avatar.video_display import get_display

    while True:
        try:
            audio_path = _job_queue.get(timeout=5)
        except queue.Empty:
            continue

        # Convert to absolute path — Wav2Lip chạy với cwd khác nên relative path sẽ sai
        audio_path = os.path.abspath(audio_path)

        if not os.path.exists(audio_path):
            util.log(2, f"[LipSync] Audio không tồn tại: {audio_path}")
            continue

        face_input = _get_face_input()
        if not face_input:
            util.log(2, "[LipSync] Chưa có file avatar. Đặt avatar vào avatar/assets/avatar.jpg hoặc avatar_idle.mp4")
            continue

        output_path = os.path.join(
            config.OUTPUT_DIR,
            f"lipsync_{int(time.time() * 1000)}.mp4"
        )

        util.log(1, f"[LipSync] Bắt đầu xử lý: {os.path.basename(audio_path)}")
        t0 = time.time()

        success = _run_wav2lip(face_input, audio_path, output_path)

        if success:
            elapsed = round(time.time() - t0, 1)
            util.log(1, f"[LipSync] Hoàn thành trong {elapsed}s → {os.path.basename(output_path)}")
            get_display().play_lipsync(output_path)
        else:
            util.log(2, "[LipSync] Wav2Lip thất bại, bỏ qua")


def _get_env_with_ffmpeg() -> dict:
    """Trả về environ với ffmpeg từ imageio trong PATH."""
    env = os.environ.copy()
    try:
        import imageio_ffmpeg
        ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        env['PATH'] = ffmpeg_dir + os.pathsep + env.get('PATH', '')
    except Exception:
        pass
    return env


def _run_wav2lip(face: str, audio: str, output: str) -> bool:
    cmd = [
        sys.executable,
        config.WAV2LIP_INFERENCE,
        "--checkpoint_path", config.WAV2LIP_CHECKPOINT,
        "--face", face,
        "--audio", audio,
        "--outfile", output,
        "--resize_factor", "4",  # CPU-friendly: giảm resolution → nhanh hơn ~4x
        "--nosmooth",
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=config.WAV2LIP_DIR,
            capture_output=True,
            text=True,
            timeout=300,
            env=_get_env_with_ffmpeg(),
        )
        if result.returncode != 0:
            util.log(2, f"[LipSync] Wav2Lip error: {result.stderr[-500:]}")
            return False
        return os.path.exists(output)
    except subprocess.TimeoutExpired:
        util.log(2, "[LipSync] Wav2Lip timeout (>120s)")
        return False
    except Exception as e:
        util.log(2, f"[LipSync] Exception: {e}")
        return False
