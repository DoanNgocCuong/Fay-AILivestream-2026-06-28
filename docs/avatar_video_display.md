# Avatar Video Display — Tài liệu kỹ thuật đầy đủ

**File nguồn:** `avatar/video_display.py`
**Cập nhật:** 2026-06-28

---

## 1. Bài toán cần giải quyết

Fay AI cần một cửa sổ video để dùng làm nguồn cho OBS Livestream. Yêu cầu:

1. **Khi không có comment:** Phát video avatar lặp vô tận (có tiếng nhạc/âm thanh nếu video có)
2. **Khi AI trả lời:** Chuyển sang phát video nhép môi (Wav2Lip output), có tiếng AI nói
3. **Sau khi xong:** Quay lại chế độ loop

**Vấn đề khó:** Python/OpenCV không phát được audio từ mp4. Phải giải quyết thủ công.

---

## 2. Tổng quan giải pháp

```
mp4 file
  ├── video track  →  OpenCV (cv2.VideoCapture)  →  hiển thị từng frame
  └── audio track  →  ffmpeg extract → .wav file  →  pygame.mixer phát
                                                          ↑
                                                   cả 2 start cùng lúc
                                                   + sync liên tục để không lệch
```

Ba thư viện chính:
- **OpenCV** (`cv2`): đọc và hiển thị từng frame video
- **pygame** (`pygame.mixer`): phát file audio `.wav`
- **imageio-ffmpeg**: cung cấp binary `ffmpeg.exe` để tách audio từ mp4

---

## 3. Cài đặt từ đầu

### 3.1 Cài thư viện

```bash
pip install opencv-python pygame imageio-ffmpeg numpy
```

Kiểm tra sau khi cài:

```python
import cv2; print("cv2 OK")
import pygame; print("pygame OK")
import imageio_ffmpeg; print("ffmpeg:", imageio_ffmpeg.get_ffmpeg_exe())
```

### 3.2 Chuẩn bị file avatar

```
avatar/
  assets/
    avatar_idle.mp4     ← video phát khi chờ (có thể có audio, có thể không)
    avatar.jpg          ← ảnh tĩnh fallback nếu không có video
```

Video `avatar_idle.mp4` đang dùng là `data/Facebook.mp4` đã copy vào.

---

## 4. Cấu trúc file `video_display.py` — từng phần

### 4.1 Import và khởi tạo pygame

```python
try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
    _pygame_available = True
except Exception:
    _pygame_available = False
```

**Tại sao dùng try/except?**
Nếu `pygame` chưa cài, chương trình vẫn chạy được — chỉ là không có tiếng. Đây gọi là "graceful degradation".

**Tham số `mixer.init`:**
- `frequency=44100`: sample rate chuẩn CD
- `size=-16`: 16-bit signed PCM
- `channels=2`: stereo
- `buffer=512`: buffer nhỏ → latency thấp (quan trọng cho lip sync)

### 4.2 Tìm đường dẫn ffmpeg

```python
def _get_ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"  # thử dùng system ffmpeg nếu imageio không có
```

`imageio_ffmpeg` bundle sẵn file `ffmpeg.exe` trong package Python — không cần người dùng tự cài ffmpeg. Đường dẫn thực tế trông như:
```
C:\Users\...\site-packages\imageio_ffmpeg\binaries\ffmpeg-win-x86_64-v7.1.exe
```

### 4.3 Tách audio từ mp4 → wav

```python
def _extract_audio_wav(video_path: str) -> str | None:
    wav_path = video_path.rsplit(".", 1)[0] + "_audio.wav"
    if os.path.exists(wav_path):
        return wav_path  # đã extract rồi, dùng lại
    result = subprocess.run(
        [_get_ffmpeg_exe(), "-y", "-i", video_path,
         "-vn",              # video: không lấy
         "-acodec", "pcm_s16le",  # audio codec: PCM 16-bit little-endian
         "-ar", "44100",    # sample rate
         "-ac", "2",        # stereo
         wav_path],
        capture_output=True, timeout=30
    )
    return wav_path if result.returncode == 0 else None
```

**Tại sao cần tách ra wav?**
`pygame.mixer` chỉ đọc được `.wav` hoặc `.ogg`, không đọc được audio track trong `.mp4` trực tiếp.

**Tên file wav:** `avatar_idle.mp4` → `avatar_idle_audio.wav` (lưu cạnh file gốc, cache lại).

### 4.4 Phát và dừng audio

```python
def _play_audio(wav_path):
    pygame.mixer.music.load(wav_path)
    pygame.mixer.music.play()

def _stop_audio():
    pygame.mixer.music.stop()
```

`pygame.mixer.music` chạy trong thread riêng của pygame — không block Python code.

### 4.5 Tự fit cửa sổ vào màn hình

```python
def _fit_to_screen(video_w, video_h, margin=0.9):
    # Lấy kích thước màn hình qua tkinter
    root = tk.Tk(); root.withdraw()
    screen_w = root.winfo_screenwidth()
    screen_h = root.winfo_screenheight()
    root.destroy()

    max_w = int(screen_w * margin)  # 90% chiều rộng màn hình
    max_h = int(screen_h * margin)
    scale = min(max_w / video_w, max_h / video_h, 1.0)  # không bao giờ phóng to
    return int(video_w * scale), int(video_h * scale)
```

Ví dụ: Video 1080x1920 (portrait), màn hình 1920x1080 → cửa sổ sẽ là 607x1080 (fit chiều cao 90%).

---

## 5. Class `VideoDisplay` — trái tim của module

### 5.1 Hai chế độ hoạt động

```python
_MODE_IDLE = "idle"       # đang loop video nền
_MODE_SPEAKING = "speaking"  # đang phát lip sync
```

Biến `self._mode` được đọc/ghi bằng `self._lock` (threading.Lock) để tránh race condition.

### 5.2 Vòng lặp chính `_run()`

```python
def _run(self):
    # 1. Mở video idle
    self._idle_cap = cv2.VideoCapture("avatar/assets/avatar_idle.mp4")

    # 2. Đọc FPS và kích thước thực của video
    actual_fps = self._idle_cap.get(cv2.CAP_PROP_FPS)
    actual_w = int(self._idle_cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(self._idle_cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # 3. Tạo cửa sổ OpenCV
    cv2.namedWindow("Linh - Dr.Bee AI Host", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Linh - Dr.Bee AI Host", display_w, display_h)

    # 4. Tách audio idle ra wav (lần đầu)
    self._idle_audio_wav = _extract_audio_wav("avatar/assets/avatar_idle.mp4")

    # 5. Vòng lặp vô tận
    while self._running:
        if mode == "speaking":
            self._play_once(speak_video_path)  # phát lip sync
        else:
            self._show_idle_frame()            # phát idle

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break  # nhấn Q để thoát
```

### 5.3 `_show_idle_frame()` — phát idle loop

```python
def _show_idle_frame(self):
    # Lần đầu tiên: bắt đầu phát audio
    if not self._idle_audio_playing:
        _play_audio(self._idle_audio_wav)
        self._idle_audio_playing = True

    # AUDIO-CLOCK SYNC: kiểm tra audio đang ở giây thứ mấy
    audio_pos_ms = pygame.mixer.music.get_pos()
    if audio_pos_ms >= 0:
        target_frame = int((audio_pos_ms / 1000.0) * fps)
        current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
        gap = target_frame - current_frame

        if gap > 1:   # video bị chậm → nhảy tới frame đúng
            cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        elif gap < -2: # video nhanh hơn audio → dừng 1 frame
            time.sleep(1 / fps)
            return

    # Đọc và hiển thị frame
    ret, frame = cap.read()
    if not ret:
        # Video hết → loop lại từ đầu
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        pygame.mixer.music.rewind()
        pygame.mixer.music.play()

    cv2.imshow("Linh - Dr.Bee AI Host", frame)
    time.sleep(1 / fps / 2)  # sleep ngắn, sync xử lý timing chính
```

**Tại sao cần audio-clock sync?**
Không thể dùng `time.sleep(1/fps)` chính xác 100% vì:
- `cv2.imshow` tốn thời gian khác nhau tùy frame
- CPU load thay đổi → sleep bị drift
- Sau 30 giây, video có thể lệch 0.5-2 giây so với audio

Giải pháp: Dùng vị trí audio (do pygame theo dõi chính xác) làm "đồng hồ chuẩn", video phải đuổi theo audio.

### 5.4 `_play_once()` — phát lip sync video

```python
def _play_once(self, video_path):
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)

    # Tách audio và phát ngay
    wav = _extract_audio_wav(video_path)
    _play_audio(wav)

    while self._running:
        # Kiểm tra audio đã hết chưa
        audio_pos_ms = pygame.mixer.music.get_pos()
        if audio_pos_ms < 0:
            break  # audio xong → dừng phát video

        # Sync tương tự idle
        target_frame = int((audio_pos_ms / 1000.0) * fps)
        ...

        ret, frame = cap.read()
        if not ret:
            break  # video hết frame → dừng

        cv2.imshow("Linh - Dr.Bee AI Host", frame)
        time.sleep(frame_duration / 2)

    cap.release()
    _stop_audio()
    # Sau khi xong → mode tự động về IDLE trong _run()
```

### 5.5 `_resize()` — letterbox

```python
def _resize(self, frame):
    src_ratio = w / h
    dst_ratio = target_w / target_h

    if src_ratio > dst_ratio:  # video rộng hơn window → pillar box (cột đen 2 bên)
        new_w = target_w
        new_h = int(target_w / src_ratio)
    else:                      # video cao hơn window → letter box (thanh đen trên dưới)
        new_h = target_h
        new_w = int(target_h * src_ratio)

    resized = cv2.resize(frame, (new_w, new_h))
    canvas = np.zeros((target_h, target_w, 3), dtype=np.uint8)  # nền đen
    # Paste vào giữa canvas
    y_off = (target_h - new_h) // 2
    x_off = (target_w - new_w) // 2
    canvas[y_off:y_off+new_h, x_off:x_off+new_w] = resized
    return canvas
```

---

## 6. Cách module được gọi từ Fay

### 6.1 Khi Fay khởi động (`fay_booter.py`)

```python
# Trong hàm start() của fay_booter.py
try:
    from avatar import pipeline as avatar_pipeline
    avatar_pipeline.start()  # → VideoDisplay.start() → daemon thread bắt đầu
except Exception as e:
    util.log(2, f'[Avatar] Bo qua: {e}')
```

### 6.2 Khi TTS tạo xong audio (`core/fay_core.py`)

```python
# Sau dòng: result = self.sp.to_sample(filtered_text, mood_voice)
try:
    from avatar import pipeline as avatar_pipeline
    if result:
        avatar_pipeline.on_audio_ready(result)  # result = đường dẫn file audio
except Exception:
    pass
```

### 6.3 Pipeline trung gian (`avatar/pipeline.py`)

```python
def on_audio_ready(audio_path: str):
    lip_sync.submit(audio_path)
    # → lip_sync worker thread → Wav2Lip subprocess → tạo lipsync.mp4
    # → VideoDisplay.play_lipsync(lipsync.mp4)  → mode = SPEAKING
```

---

## 7. Fallback chain — khi thiếu file/thư viện

```
Tình huống                          Xử lý
─────────────────────────────────   ──────────────────────────────────
avatar_idle.mp4 không tồn tại      → thử dùng avatar.jpg
avatar.jpg không tồn tại           → màn hình đen + text "Linh - Dr.Bee AI Host"
pygame chưa cài                    → chỉ video, không có tiếng
imageio-ffmpeg chưa cài            → thử gọi system "ffmpeg"; nếu không có → skip audio
mp4 không có audio track           → ffmpeg extract thất bại → skip audio
Wav2Lip chưa cài                   → lip_sync.py bỏ qua, không crash
```

---

## 8. Chạy thủ công để test

### Test nhanh video display độc lập:

```python
# test_display.py — chạy từ D:\GIT\Fay\
import sys
sys.path.insert(0, ".")
from avatar.video_display import get_display
import time

display = get_display()
display.start()
print("Cửa sổ đã mở. Nhấn Q trong cửa sổ để thoát.")
time.sleep(60)
display.stop()
```

```bash
cd D:\GIT\Fay
set PYTHONUTF8=1
python test_display.py
```

### Chạy Fay đầy đủ:

```bash
cd D:\GIT\Fay
set PYTHONUTF8=1
python main.py start
```

Cửa sổ **"Linh - Dr.Bee AI Host"** sẽ tự bật lên sau ~10 giây khởi động.

---

## 9. Kết nối với OBS để Livestream

1. Mở OBS
2. **Add Source → Window Capture**
3. Chọn window: `[python.exe]: Linh - Dr.Bee AI Host`
4. Scale source để fit scene (thường `Alt+drag` góc để crop)
5. **Start Streaming**

---

## 10. Sơ đồ luồng đầy đủ

```
[Fay start]
    │
    ├─ fay_booter.py
    │      └─ avatar_pipeline.start()
    │              └─ VideoDisplay.start()
    │                      └─ daemon thread ──────────────────────────────┐
    │                                                                      │
    │                                              ┌─── IDLE LOOP ◄───────┘
    │                                              │   cv2.imshow(frame)
    │                                              │   pygame.play(wav)
    │                                              │   audio-clock sync
    │                                              │   loop khi hết video
    │
[Khách comment]
    │
    ├─ Fay AI xử lý → text reply
    │
    ├─ TTS (Edge-TTS) → reply_audio.wav
    │
    ├─ fay_core.py: on_audio_ready(reply_audio.wav)
    │
    ├─ lip_sync.py (worker thread)
    │      └─ Wav2Lip inference (~3-15s tùy CPU)
    │              └─ lipsync_xxx.mp4
    │
    └─ VideoDisplay.play_lipsync(lipsync_xxx.mp4)
               └─ mode = SPEAKING
                      │
               _play_once():
                 - extract audio → wav
                 - pygame.play(wav)
                 - cv2.imshow frames
                 - audio-clock sync
                      │
               khi xong → mode = IDLE ──────────────► IDLE LOOP
```

---

## 11. Điểm cần lưu ý khi modify

| Điểm | Giải thích |
|------|-----------|
| `config.WIDTH = None` | Nếu set `None`, cửa sổ tự fit màn hình. Set số cụ thể để override. |
| `buffer=512` trong pygame | Tăng nếu bị crackling audio. Giảm nếu cần latency thấp hơn. |
| `margin=0.9` trong `_fit_to_screen` | 90% màn hình. Thay đổi nếu muốn cửa sổ to/nhỏ hơn. |
| `time.sleep(1/fps/2)` | Sleep ngắn hơn frame duration — sync xử lý timing chính, không phải sleep |
| Wav2Lip output | Hiện chưa có — chỉ IDLE loop hoạt động cho đến khi cài Wav2Lip |
| Thread safety | `self._lock` bảo vệ `_mode` và `_speak_video_path` — không access 2 biến này trực tiếp từ ngoài |
