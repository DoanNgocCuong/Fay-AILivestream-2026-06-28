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
        cv2.namedWindow(config.WINDOW_NAME, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(config.WINDOW_NAME, config.WIDTH, config.HEIGHT)

        self._idle_cap = self._open_idle_source()
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
        if self._idle_cap and self._idle_cap.isOpened():
            ret, frame = self._idle_cap.read()
            if not ret:
                # Video looped — restart audio too
                self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                self._idle_audio_playing = False
                ret, frame = self._idle_cap.read()
            if ret:
                # Start idle audio on first frame of each loop
                if not self._idle_audio_playing and self._idle_audio_wav:
                    _play_audio(self._idle_audio_wav)
                    self._idle_audio_playing = True
                frame = self._resize(frame)
                cv2.imshow(config.WINDOW_NAME, frame)
                time.sleep(1.0 / config.FPS)
                return

        # Fallback static image or black screen
        if os.path.exists(config.AVATAR_IMAGE_PATH):
            frame = cv2.imread(config.AVATAR_IMAGE_PATH)
            if frame is not None:
                frame = self._resize(frame)
                cv2.imshow(config.WINDOW_NAME, frame)
                time.sleep(1.0 / config.FPS)
                return

        blank = np.zeros((config.HEIGHT, config.WIDTH, 3), dtype=np.uint8)
        cv2.putText(blank, "Linh - Dr.Bee AI Host", (50, config.HEIGHT // 2),
                    cv2.FONT_HERSHEY_SIMPLEX, 1.5, (255, 255, 255), 2)
        cv2.imshow(config.WINDOW_NAME, blank)
        time.sleep(1.0 / config.FPS)

    def _play_once(self, video_path: str):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or config.FPS
        delay = 1.0 / fps

        # Extract and play audio for the lip-sync video
        wav = _extract_audio_wav(video_path)
        _play_audio(wav)

        while self._running:
            ret, frame = cap.read()
            if not ret:
                break
            frame = self._resize(frame)
            cv2.imshow(config.WINDOW_NAME, frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                self._running = False
                break
            time.sleep(delay)
        cap.release()
        _stop_audio()

    def _resize(self, frame: np.ndarray) -> np.ndarray:
        return cv2.resize(frame, (config.WIDTH, config.HEIGHT))


_instance: VideoDisplay | None = None
_instance_lock = threading.Lock()


def get_display() -> VideoDisplay:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = VideoDisplay()
        return _instance
