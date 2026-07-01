"""
Pre-compute "golden frames" — điểm dừng đẹp trong idle video.

Golden frame = frame có motion thấp (optical flow) VÀ trùng với khoảng
lặng trong audio track.  Kết quả được cache sau lần tính đầu tiên.

Dùng: get_golden_frames(video_path) → list[int] (sorted frame indices)
"""
import os
import wave
import struct
import threading
import time

import cv2
import numpy as np

from utils import util

# Tham số tuneable
_MOTION_THRESHOLD = 1.5      # mean optical flow magnitude, đơn vị pixel/frame
_SILENCE_THRESHOLD = 0.05    # RMS tỉ lệ, 0-1 (0.05 = 5% max amplitude)
_MIN_GOLDEN_FRAMES = 8       # nếu merge quá ít, fallback chỉ dùng motion
_MAX_PROCESS_FRAMES = 0      # 0 = toàn bộ video; giới hạn nếu video quá dài

_cache: dict[str, list[int]] = {}
_cache_lock = threading.Lock()


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_golden_frames(video_path: str) -> list[int]:
    """Trả về list frame indices đã sort. Có thể rỗng nếu chưa compute xong."""
    with _cache_lock:
        return _cache.get(video_path, [])


def precompute_async(video_path: str):
    """Bắt đầu tính golden frames trong background thread (non-blocking)."""
    if not os.path.exists(video_path):
        return
    with _cache_lock:
        if video_path in _cache:
            return  # đã có cache rồi
    t = threading.Thread(target=_precompute, args=(video_path,), daemon=True)
    t.start()


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _precompute(video_path: str):
    t0 = time.time()
    util.log(1, "[Startup] Pre-compute stillness — dang quet video de tim cac golden frames (diem avatar dung yen nhat)...")

    motion_scores = _compute_motion_scores(video_path)
    if not motion_scores:
        util.log(2, "[Stillness] Không đọc được video để tính motion")
        return

    silence_mask = _compute_silence_mask(video_path, len(motion_scores))
    golden = _merge(motion_scores, silence_mask)

    with _cache_lock:
        _cache[video_path] = golden

    elapsed = round(time.time() - t0, 1)
    total = len(motion_scores)
    util.log(1, f"[Startup] Pre-compute stillness xong ({elapsed}s): {len(golden)}/{total} golden frames — ty le {round(len(golden)/total*100)}% frame avatar dung yen, dung lam diem dung khi chen lipsync vao video")


def _compute_motion_scores(video_path: str) -> list[float]:
    """Tính optical flow magnitude trung bình cho mỗi frame."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    scores: list[float] = []
    prev_gray = None
    frame_idx = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.resize(gray, (320, 180))  # nhỏ lại để tính nhanh hơn

        if prev_gray is None:
            scores.append(0.0)  # frame đầu coi như tĩnh
        else:
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray, gray,
                None,
                pyr_scale=0.5, levels=3, winsize=15,
                iterations=3, poly_n=5, poly_sigma=1.2,
                flags=0,
            )
            mag = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            scores.append(float(mag.mean()))

        prev_gray = gray
        frame_idx += 1
        if _MAX_PROCESS_FRAMES > 0 and frame_idx >= _MAX_PROCESS_FRAMES:
            break

    cap.release()
    return scores


def _compute_silence_mask(video_path: str, num_frames: int) -> list[bool]:
    """
    Trả về boolean mask: True = frame này trùng với khoảng lặng trong audio.
    Dùng ffmpeg extract wav (đã có sẵn trong video_display), sau đó đọc trực tiếp.
    """
    wav_path = video_path.rsplit(".", 1)[0] + "_audio.wav"
    if not os.path.exists(wav_path):
        # Không có wav → coi tất cả là "không lặng" (chỉ dùng motion)
        return [False] * num_frames

    try:
        return _wav_silence_mask(wav_path, num_frames)
    except Exception as e:
        util.log(2, f"[Stillness] Lỗi đọc audio: {e}")
        return [False] * num_frames


def _wav_silence_mask(wav_path: str, num_frames: int) -> list[bool]:
    with wave.open(wav_path, "rb") as wf:
        n_channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        framerate = wf.getframerate()
        n_samples = wf.getnframes()

        # Chỉ đọc raw bytes
        raw = wf.readframes(n_samples)

    # Parse sang numpy
    if sampwidth == 2:
        samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sampwidth == 4:
        samples = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2**31
    else:
        return [False] * num_frames

    if n_channels > 1:
        samples = samples[::n_channels]  # lấy channel đầu tiên

    # Lấy FPS từ video để biết mỗi frame = bao nhiêu samples
    # Ước tính: num_frames * fps = video_duration; samples = audio_duration * framerate
    # fps ≈ num_frames * framerate / len(samples) — nhưng ta không biết fps chính xác ở đây
    # → dùng tỉ lệ trực tiếp
    samples_per_frame = max(1, len(samples) // max(1, num_frames))

    mask: list[bool] = []
    for i in range(num_frames):
        start = i * samples_per_frame
        end = min(start + samples_per_frame, len(samples))
        chunk = samples[start:end]
        if len(chunk) == 0:
            mask.append(False)
            continue
        rms = float(np.sqrt(np.mean(chunk ** 2)))
        mask.append(rms < _SILENCE_THRESHOLD)

    return mask


def _merge(motion_scores: list[float], silence_mask: list[bool]) -> list[int]:
    """Kết hợp motion + silence → chọn golden frames."""
    n = len(motion_scores)

    # Tìm low-motion frames
    low_motion = [i for i, s in enumerate(motion_scores) if s < _MOTION_THRESHOLD]

    # Tìm merged (low motion AND silence)
    if len(silence_mask) == n:
        merged = [i for i in low_motion if silence_mask[i]]
    else:
        merged = []

    # Nếu merged đủ nhiều → dùng merged; không thì fallback motion-only
    if len(merged) >= _MIN_GOLDEN_FRAMES:
        return sorted(merged)
    if len(low_motion) >= _MIN_GOLDEN_FRAMES:
        return sorted(low_motion)

    # Fallback: lấy bottom 30% motion scores
    threshold = float(np.percentile(motion_scores, 30)) if motion_scores else _MOTION_THRESHOLD
    fallback = [i for i, s in enumerate(motion_scores) if s <= threshold]
    return sorted(fallback) if fallback else list(range(n))


def next_golden_frame(video_path: str, current_frame: int, total_frames: int) -> int | None:
    """
    Tìm golden frame tiếp theo >= current_frame trong vòng lặp video.
    Returns None nếu chưa có data.

    Nếu không tìm thấy phía sau → wrap around (lấy frame đầu tiên trong list).
    """
    frames = get_golden_frames(video_path)
    if not frames:
        return None

    # Tìm frame đầu tiên >= current_frame
    for f in frames:
        if f >= current_frame:
            return f

    # Wrap around: lấy frame đầu tiên (lần loop kế tiếp)
    return frames[0]
