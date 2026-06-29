# Phase 1 — AI Livestream Local: Implementation Record

**Thời gian:** 2026-06-28, 14h00–18h30
**Trạng thái:** ✅ Success #1, #2, #3 hoàn thành | ⏳ Success #4 đang research

---

## Mục tiêu Phase 1

Chạy được AI Avatar Livestream hoàn chỉnh trên máy local:
- AI nghe comment → trả lời bằng giọng nói tiếng Việt
- Avatar video phát liên tục có tiếng
- Khi AI reply: video dừng, nhép môi khớp lời nói, xong video chạy tiếp
- OBS capture cửa sổ avatar → stream lên Facebook Live

---

## Success #1 — AI reply Audio tiếng Việt trong < 1 giây

**Hoàn thành:** 14h30, 2026-06-28 | **Commit:** `4abd566`

### Vấn đề cần giải quyết

Khách chat trên livestream → AI phải phản hồi ngay bằng giọng nói. Nếu delay > 2s khách mất tin tưởng.

**Nỗi đau cụ thể:** Pipeline cũ xử lý tuần tự — LLM phải generate xong toàn bộ response rồi mới bắt đầu TTS. Với câu trả lời dài 3-4 câu, delay lên đến 5-8s.

Thêm vào đó: Fay gốc có 5 câu status nội bộ bằng tiếng Trung (ví dụ: `"等等..."`, `"我来帮你查..."`) — Edge-TTS không đọc được tiếng Trung → crash với lỗi `No audio was received`.

### Giải pháp

**LLM streaming + TTS early trigger:**
```
Fay framework: WebSocket nhận comment
  → Gemini 2.5 Flash stream response (chunk by chunk)
  → Phát TTS ngay khi có chunk đầu tiên (không đợi full response)
  → Edge-TTS (vi-VN-HoaiMyNeural) → pygame audio output
```

**Tách luồng:** LLM thread độc lập với display thread — không block nhau.

**Fix 5 câu status nội bộ:** Dịch từ tiếng Trung sang tiếng Việt trong `llm/nlp_cognitive_stream.py`:

| Trước (tiếng Trung, TTS crash) | Sau (tiếng Việt) |
|-------------------------------|-----------------|
| `等等...` | `Để Linh xác nhận lại thông tin cho bạn nhé...` |
| `我来帮你查...` | `Để mình kiểm tra giúp bạn, chờ chút nhé...` |
| (3 câu khác tương tự) | → tiếng Việt tự nhiên |

**Persona & Knowledge:**
- `config.json`: nhân vật **Linh** — AI sales host Dr.Bee Nhộng Ong Haircare
- `qa.csv`: 16 cặp Q&A tiếng Việt (bảng giá, thành phần, công dụng, cách dùng)
- System prompt: tư vấn bán hàng, xử lý objection, upsell combo 590K
- TTS voice: `Hoài My (vi-VN-HoaiMyNeural)` + `Nam Minh (vi-VN-NamMinhNeural)`

**UI Việt hoá (5 files):** `index.html`, `setting.html`, `setting.js`, `script.js`, `flask_server.py`

**Tooling:**
- `START_DEMO.bat`: launcher Windows 1-click
- `OBS_SETUP_GUIDE.md`: hướng dẫn kết nối OBS → Facebook Live
- `system.conf` → `.gitignore`, tạo `system.conf.example` (tránh lộ API key)

### Kết quả đạt được
- Khách gửi comment → nghe tiếng AI reply trong **< 1 giây**
- Giọng Hoài My tự nhiên, đúng tiếng Việt
- Không crash khi nhiều comment liên tiếp
- Icon mấp máy miệng góc trái màn hình (built-in Fay, không cần code thêm)

---

## Success #2 — Video Loop liên tục + Audio A/V Sync + Auto-fit Window

**Hoàn thành:** 16h00, 2026-06-28 | **Commit:** `0d5f653`

### Vấn đề cần giải quyết

Cần một cửa sổ video avatar phát liên tục có tiếng để OBS capture. Khi AI reply thì video dừng phát audio AI, xong lại chạy tiếp.

**Nỗi đau cụ thể:**
1. OpenCV (`cv2`) không phát audio từ mp4 — chỉ decode video frames
2. Hai timer độc lập (pygame clock + `time.sleep`) tích lũy drift — sau 30s video lệch audio ~1-2s
3. Video hardcode `FPS=25` nhưng `Facebook.mp4` là 30fps → video chậm hơn audio 17%
4. Sau khi AI nói xong, video bị **freeze** (không resume)

### Giải pháp

**Tách audio từ mp4 → wav, phát bằng pygame:**
```python
# imageio_ffmpeg: bundle sẵn ffmpeg.exe trong pip package
ffmpeg -i avatar_idle.mp4 -vn -acodec pcm_s16le -ar 44100 -ac 2 avatar_idle_audio.wav
pygame.mixer.music.load(wav_path)
pygame.mixer.music.play()
```

**Audio-clock-driven sync — dùng pygame làm master clock:**
```python
audio_pos_ms = pygame.mixer.music.get_pos()   # hardware clock, chính xác
target_frame = int((audio_pos_ms / 1000.0) * fps)
current_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
gap = target_frame - current_frame

if gap > 1:    # video chậm → skip frames bắt kịp
    cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
elif gap < -2: # video nhanh → đợi 1 frame
    time.sleep(1 / fps)
```

**Auto-detect FPS + kích thước từ video thực tế:**
```python
actual_fps = cap.get(cv2.CAP_PROP_FPS)   # đọc 30fps thay vì hardcode 25
actual_w   = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
actual_h   = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
```

**Auto-fit window vào màn hình (letterbox):**
```python
def _fit_to_screen(video_w, video_h, margin=0.9):
    scale = min(max_w / video_w, max_h / video_h, 1.0)  # không upscale
    return int(video_w * scale), int(video_h * scale)
```

**2 mode IDLE / SPEAKING:**

| Mode | Hành vi |
|------|---------|
| IDLE | Loop video + audio liên tục. Khi video hết: `rewind()` + `play()` restart đồng bộ |
| SPEAKING | Dừng idle audio, phát lipsync video 1 lần, xong về IDLE |

**Fix bug freeze sau SPEAKING:**
```python
# Root cause: idle_cap ở frame N sau khi SPEAKING kết thúc
# Audio restart từ 0 → gap = 0 - N = rất âm → return ngay → đóng hình
# Fix:
if self._idle_cap:
    self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)  # reset về 0 sau SPEAKING→IDLE
```

**Fix BOM trong system.conf:**
```python
encoding='utf-8-sig'  # tự strip BOM ﻿ nếu có
```

**Fix embedding spam 400 error:**
```python
# Chỉ enable embedding nếu embedding_api_model được set rõ
# Nếu trống → skip API, dùng mock vector → không spam log
```

### Kết quả đạt được
- Video idle loop liên tục, có tiếng, không ngắt
- Audio/video không lệch nhau dù chạy hàng giờ
- Cửa sổ tự fit 90% màn hình, giữ aspect ratio
- Khi AI reply: video dừng → audio phát → video tiếp tục (không freeze)

---

## Success #3 — Wav2Lip Lip Sync: Nhép môi khớp Audio + Blend vào Video

**Hoàn thành:** 18h30, 2026-06-28 | **Commits:** `a7ada5f`, `3a19c35`

### Vấn đề cần giải quyết

Pipeline cũ: phát audio ngay (<1s) → **sau đó** mới gen lipsync (~60 phút CPU) → kết quả: khách nghe tiếng AI nhưng **không thấy môi nhép**.

Cần: CHỈ phát khi lipsync video đã sẵn sàng, để audio và video lip-sync cùng nhau.

### Giải pháp

#### Bước 1 — Cài đặt Wav2Lip + Compatibility Patches (Python 3.12)

```bash
# Wav2Lip làm git submodule
git submodule add https://github.com/Rudrabha/Wav2Lip avatar/Wav2Lip

# Checkpoint: wav2lip_gan.pth (435MB) từ HuggingFace
# Không commit → .gitignore
```

**Patches Python 3.12 + librosa 0.11 + torch 2.9:**

| File | Vấn đề | Fix |
|------|--------|-----|
| `avatar/Wav2Lip/audio.py` | `librosa.filters.mel()` không nhận positional args (librosa 0.11) | Đổi sang keyword args |
| `avatar/Wav2Lip/inference.py` | `imageio_ffmpeg.get_ffmpeg_exe()` trả path không tồn tại → WinError 2 sau **60 phút** inference | Check `os.path.isfile()` trước, fallback `shutil.which('ffmpeg')` |
| `avatar/lip_sync.py` | system ffmpeg không có trong PATH | `_get_env_with_ffmpeg()`: inject imageio ffmpeg vào PATH khi gọi subprocess |

**Tối ưu tốc độ CPU:**
```bash
--resize_factor 4   # giảm resolution 4x → inference nhanh hơn ~4x
--nosmooth          # bỏ smoothing → nhanh hơn
timeout: 120s → 300s  # câu dài hơn cần thêm thời gian
```

**Kết quả test:** Audio 4.3s → inference ~103s trên CPU (resize_factor=4)

#### Bước 2 — Pipeline: Skip Audio cho đến khi Lipsync Ready

**Trước:**
```
TTS xong → phát audio ngay (<1s) → [60 phút sau] lipsync video phát (double audio)
```

**Sau:**
```
TTS xong → on_audio_ready() → True (Wav2Lip available)
  → SKIP phát audio ngay
  → [10-20s Wav2Lip inference async]
  → Lipsync video (có audio embedded) → VideoDisplay.play_lipsync()
  → Khách thấy môi nhép + nghe tiếng cùng lúc ✅

Nếu Wav2Lip fail → fallback_play_audio() phát audio trực tiếp
  → Khách không biết có lỗi ✅
```

**`pipeline.py` — `on_audio_ready()` trả `bool`:**
```python
def on_audio_ready(audio_path: str) -> bool:
    if wav2lip_available:
        lip_sync.submit(audio_path)
        return True   # caller skip Fay audio pipeline
    return False      # caller tự phát audio bình thường
```

**`core/fay_core.py` — check return value:**
```python
_lipsync_handles_audio = False  # init ở function scope (fix UnboundLocalError)
# ...sau TTS...
_lipsync_handles_audio = avatar_pipeline.on_audio_ready(result)
if not _lipsync_handles_audio:
    self.__process_output_audio(result)  # phát audio bình thường
```

**`lip_sync.py` — fallback audio khi Wav2Lip fail:**
```python
def _fallback_play_audio(audio_path):
    # Dùng pygame.mixer.Sound (channel riêng)
    # KHÔNG dùng .music channel của idle video (tránh conflict)
    sound = pygame.mixer.Sound(audio_path)
    sound.play()
```

#### Bugs đã fix trong Success #3

**Bug 1 — Video lipsync không hiển thị khi audio extract fail:**
```
Root cause: wav=None → pygame.get_pos()=-1 → break ngay trước frame 1
Fix: use_audio_sync = pygame_available AND wav is not None
     Nếu không có audio → time-based playback thay thế
```

**Bug 2 — UnboundLocalError `_lipsync_handles_audio`:**
```
Root cause: biến được dùng ở ngoài if-block nhưng chỉ assign bên trong
Fix: init _lipsync_handles_audio = False tại đầu function scope
```

### Kết quả đạt được
- Khách thấy môi nhép đúng với lời nói AI
- Audio và video sync (không lệch)
- Nếu Wav2Lip fail: audio vẫn phát, khách không biết
- Video sau khi speak xong tự resume idle

### Hạn chế hiện tại
- Wav2Lip CPU rất chậm: ~103s/clip 4.3s → **không real-time** được trên CPU
- Cần GPU (NVIDIA) hoặc cloud API để production
- `resize_factor=4` làm chất lượng nhép môi giảm nhẹ

---

## Success #4 — Smart Insertion Point (Research done, chưa implement)

**Trạng thái:** Research xong — xem `3-reference/04-lipsync-insertion-point-research.md`

### Vấn đề
Hiện tại video dừng tại frame **ngẫu nhiên** khi lipsync ready → trông giật, lộ liễu.

### Giải pháp đã chọn (3 options, theo thứ tự ưu tiên)
1. **Pre-compute stillness frames** (A1+A2): phân tích optical flow + audio silence lúc startup, lưu danh sách "điểm vàng" để dừng
2. **Look-ahead buffer scoring** (B1): buffer 3s frame sắp tới, score realtime, pause tại frame tốt nhất
3. **AI timing predictor** (D3): dự đoán khi nào Wav2Lip xong, schedule pause từ sớm

### Files sẽ sửa khi implement
- `avatar/video_display.py`: thêm `_precompute_good_frames()`, sửa logic pause
- `avatar/pipeline.py`: thêm timing predictor
- `avatar/config.py`: thêm `MOTION_THRESHOLD`, `SILENCE_THRESHOLD`

---

## Tổng kết Phase 1

| Task | Status | Thời gian | Commit |
|------|--------|-----------|--------|
| 1.1 AI reply Audio < 1s | ✅ Done | 14h30 | `4abd566` |
| 1.2 Video loop + A/V sync | ✅ Done | 16h00 | `0d5f653` |
| 1.3 Wav2Lip lip sync end-to-end | ✅ Done | 18h30 | `3a19c35` |
| 1.4 Smart insertion point | ⏳ Research done | — | `b2536ee` |

**Tiến độ:** 3.5/4 = **~85%** Phase 1 hoàn thành
