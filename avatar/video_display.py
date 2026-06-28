"""
Video display with 2 modes:
- IDLE: loop background video continuously (with audio)
- SPEAKING: play lip-synced video with audio, then return to IDLE
"""
import subprocess
import threading
import time
import os
import cv2
import numpy as np
from avatar import config

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    _pygame_available = True
except Exception:
    _pygame_available = False


def _get_ffmpeg_exe() -> str:
    """Return ffmpeg executable path — prefers system ffmpeg, falls back to imageio bundle."""
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"


def _extract_audio_wav(video_path: str) -> str | None:
    """Extract audio from mp4 to a .wav file. Returns path or None if no audio/ffmpeg."""
    wav_path = video_path.rsplit(".", 1)[0] + "_audio.wav"
    if os.path.exists(wav_path):
        return wav_path
    try:
        result = subprocess.run(
            [_get_ffmpeg_exe(), "-y", "-i", video_path, "-vn", "-acodec", "pcm_s16le",
             "-ar", "44100", "-ac", "2", wav_path],
            capture_output=True, timeout=30
        )
        return wav_path if result.returncode == 0 and os.path.exists(wav_path) else None
    except Exception:
        return None


def _play_audio(wav_path: str | None):
    """Play wav file with pygame mixer. No-op if pygame unavailable or no audio."""
    if not _pygame_available or not wav_path:
        return
    try:
        pygame.mixer.music.load(wav_path)
        pygame.mixer.music.play()
    except Exception:
        pass


def _stop_audio():
    if _pygame_available:
        try:
            pygame.mixer.music.stop()
        except Exception:
            pass


def _fit_to_screen(video_w: int, video_h: int, margin: float = 0.9) -> tuple[int, int]:
    """Scale video dimensions to fit within screen bounds, keeping aspect ratio."""
    try:
        import tkinter as tk
        root = tk.Tk()
        root.withdraw()
        screen_w = root.winfo_screenwidth()
        screen_h = root.winfo_screenheight()
        root.destroy()
    except Exception:
        screen_w, screen_h = 1920, 1080

    max_w = int(screen_w * margin)
    max_h = int(screen_h * margin)
    scale = min(max_w / video_w, max_h / video_h, 1.0)  # never upscale
    return int(video_w * scale), int(video_h * scale)


def _precise_sleep(frame_start: float, frame_duration: float):
    """Sleep the exact remaining time for this frame, minus processing overhead."""
    elapsed = time.perf_counter() - frame_start
    remaining = frame_duration - elapsed
    if remaining > 0:
        time.sleep(remaining)


_MODE_IDLE = "idle"
_MODE_SPEAKING = "speaking"


class VideoDisplay:
    def __init__(self):
        self._mode = _MODE_IDLE
        self._lock = threading.Lock()
        self._running = False
        self._thread = None
        self._speak_video_path = None
        self._idle_cap = None
        self._idle_audio_wav: str | None = None
        self._idle_audio_playing = False
        self._idle_fps = config.FPS
        self._display_w = config.WIDTH or 720
        self._display_h = config.HEIGHT or 1280
        self._idle_audio_start: float = 0.0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        _stop_audio()
        if self._thread:
            self._thread.join(timeout=3)
        cv2.destroyAllWindows()

    def play_lipsync(self, video_path: str):
        with self._lock:
            self._speak_video_path = video_path
            self._mode = _MODE_SPEAKING

    def _run(self):
        self._idle_cap = self._open_idle_source()

        # Auto-detect dimensions and FPS from actual video
        if self._idle_cap:
            actual_fps = self._idle_cap.get(cv2.CAP_PROP_FPS)
            actual_w = int(self._idle_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self._idle_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_fps > 0:
                self._idle_fps = actual_fps
            if actual_w > 0 and actual_h > 0 and config.WIDTH is None:
                self._display_w, self._display_h = _fit_to_screen(actual_w, actual_h)

        cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(config.WINDOW_NAME, self._display_w, self._display_h)
        # Pre-extract idle audio once
        if self._idle_cap and os.path.exists(config.AVATAR_VIDEO_PATH):
            self._idle_audio_wav = _extract_audio_wav(config.AVATAR_VIDEO_PATH)

        while self._running:
            with self._lock:
                mode = self._mode
                speak_path = self._speak_video_path

            if mode == _MODE_SPEAKING and speak_path and os.path.exists(speak_path):
                self._idle_audio_playing = False
                _stop_audio()
                self._play_once(speak_path)
                with self._lock:
                    self._mode = _MODE_IDLE
                    self._speak_video_path = None
                # Reset idle video to frame 0 so audio-clock sync doesn't stall
                # (idle_cap was at an arbitrary frame when SPEAKING started)
                if self._idle_cap:
                    self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            else:
                self._show_idle_frame()

            if cv2.waitKey(1) & 0xFF == ord('q'):
                self._running = False
                break

        self._running = False
        _stop_audio()
        if self._idle_cap:
            self._idle_cap.release()
        cv2.destroyAllWindows()

    def _open_idle_source(self):
        if os.path.exists(config.AVATAR_VIDEO_PATH):
            cap = cv2.VideoCapture(config.AVATAR_VIDEO_PATH)
            if cap.isOpened():
                return cap
        return None

    def _show_idle_frame(self):
        if not (self._idle_cap and self._idle_cap.isOpened()):
            self._show_fallback()
            return

        # Start audio on first frame and record the exact start time
        if not self._idle_audio_playing and self._idle_audio_wav:
            _play_audio(self._idle_audio_wav)
            self._idle_audio_start = time.perf_counter()
            self._idle_audio_playing = True

        # Audio-clock-driven sync: find which frame should be showing RIGHT NOW
        if self._idle_audio_playing and _pygame_available:
            audio_pos_ms = pygame.mixer.music.get_pos()  # ms since play(), -1 if stopped
            if audio_pos_ms >= 0:
                target_frame = int((audio_pos_ms / 1000.0) * self._idle_fps)
                current_frame = int(self._idle_cap.get(cv2.CAP_PROP_POS_FRAMES))
                gap = target_frame - current_frame
                if gap > 1:
                    # Video behind audio → skip frames to catch up
                    self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                elif gap < -2:
                    # Video ahead of audio (unusual) → wait one frame duration
                    time.sleep(1.0 / self._idle_fps)
                    return

        ret, frame = self._idle_cap.read()
        if not ret:
            # Video looped — restart audio and seek back to 0
            self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self._idle_audio_playing = False
            if _pygame_available:
                pygame.mixer.music.rewind()
                pygame.mixer.music.play()
                self._idle_audio_playing = True
            ret, frame = self._idle_cap.read()

        if ret:
            frame = self._resize(frame)
            cv2.imshow(config.WINDOW_NAME, frame)
        time.sleep(1.0 / self._idle_fps / 2)  # short sleep to not spin-lock CPU

    def _show_fallback(self):
        frame_start = time.perf_counter()
        if os.path.exists(config.AVATAR_IMAGE_PATH):
            frame = cv2.imread(config.AVATAR_IMAGE_PATH)
            if frame is not None:
                cv2.imshow(config.WINDOW_NAME, self._resize(frame))
                _precise_sleep(frame_start, 1.0 / self._idle_fps)
                return
        blank = np.zeros((self._display_h, self._display_w, 3), dtype=np.uint8)
        cv2.putText(blank, "Linh - Dr.Bee AI Host", (50, self._display_h // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        cv2.imshow(config.WINDOW_NAME, blank)
        _precise_sleep(frame_start, 1.0 / self._idle_fps)

    def _play_once(self, video_path: str):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or config.FPS
        frame_duration = 1.0 / fps

        wav = _extract_audio_wav(video_path)
        _play_audio(wav)
        # Only use audio sync when we successfully started audio playback
        use_audio_sync = _pygame_available and wav is not None

        while self._running:
            if use_audio_sync:
                # Audio-clock-driven sync: seek video to match audio position
                audio_pos_ms = pygame.mixer.music.get_pos()
                if audio_pos_ms < 0:
                    break  # audio finished → video done
                target_frame = int((audio_pos_ms / 1000.0) * fps)
                current_frame = int(cap.get(cv2.CAP_PROP_POS_FRAMES))
                gap = target_frame - current_frame
                if gap > 1:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
                elif gap < -2:
                    time.sleep(frame_duration)
                    continue

            ret, frame = cap.read()
            if not ret:
                break  # video finished (time-based path, or audio-sync fallback)
            frame = self._resize(frame)
            cv2.imshow(config.WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self._running = False
                break
            if use_audio_sync:
                time.sleep(frame_duration / 2)
            else:
                time.sleep(frame_duration)  # time-based playback when no audio

        cap.release()
        _stop_audio()

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        h, w = frame.shape[:2]
        target_w = self._display_w
        target_h = self._display_h
        # Maintain aspect ratio: letterbox if needed
        src_ratio = w / h
        dst_ratio = target_w / target_h
        if abs(src_ratio - dst_ratio) < 0.01:
            # Same ratio — just resize directly, no padding needed
            return cv2.resize(frame, (target_w, target_h))
        # Different ratio — fit inside target with black bars
        if src_ratio > dst_ratio:
            new_w = target_w
            new_h = int(target_w / src_ratio)
        else:
            new_h = target_h
            new_w = int(target_h * src_ratio)
        resized = cv2.resize(frame, (new_w, new_h))
        canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)
        y_off = (target_h - new_h) // 2
        x_off = (target_w - new_w) // 2
        canvas[y_off:y_off + new_h, x_off:x_off + new_w] = resized
        return canvas


_instance: VideoDisplay | None = None
_instance_lock = threading.Lock()


def get_display() -> VideoDisplay:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = VideoDisplay()
        return _instance
