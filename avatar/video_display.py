"""
Video display với 2 chế độ:
- IDLE: loop video/ảnh nền liên tục
- SPEAKING: phát video lip-synced, xong thì về IDLE
"""
import threading
import time
import os
import cv2
import numpy as np
from avatar import config

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

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
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

        while self._running:
            with self._lock:
                mode = self._mode
                speak_path = self._speak_video_path

            if mode == _MODE_SPEAKING and speak_path and os.path.exists(speak_path):
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
                self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self._idle_cap.read()
            if ret:
                frame = self._resize(frame)
                cv2.imshow(config.WINDOW_NAME, frame)
                time.sleep(1.0 / config.FPS)
                return

        # Fallback: hiển thị ảnh tĩnh hoặc màn hình đen với text
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
