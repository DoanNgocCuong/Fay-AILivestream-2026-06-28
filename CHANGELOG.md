# CHANGELOG

All notable changes to this project will be documented in this file.

---

## [Session Report] — 2026-06-28 — 14h00–17h00 (3 tiếng siêu tập trung, không nghỉ)

> **Ghi chú cá nhân:** Pin cạn kiệt sau 3h làm việc liên tục không ngừng nghỉ.
> Héo mẹ luôn sau session này. Lẽ ra nên theo nhịp: **làm – nghỉ – làm – nghỉ**
> thì năng lượng giữ được lâu hơn thay vì đổ hết 1 lần rồi tắt ngóm.

---

### Trạng thái dự án — AI Avatar Livestream Dr.Bee

**1. ✅ ĐÃ TRIỂN KHAI XONG trong 3h:**

- Phát video avatar liên tục có tiếng (loop, không ngắt)
- Khi khách comment → AI reply bằng Audio (Edge-TTS giọng Hoài My) + Gen nhép môi (Wav2Lip)
- Video dừng lại để nhường chỗ cho audio AI phát
- Audio AI phát xong → video tự chạy tiếp
- Wav2Lip xử lý async nền (~3-15s), không block pipeline

**2. 🔄 ĐANG LÀM:**

- Ghép nhép môi khít vào phần video đang phát (thay vì phát video nhép môi riêng rẽ, cần blend mượt vào luồng video chính)

**3. ⬜ NEXT STEPS:**

- Logic đồng bộ: audio + nhép môi phải khớp chính xác với video đang phát (frame-level sync)
- Logic AI quyết định chèn (audio + nhép môi) vào **đúng điểm** trong video — tránh cắt giữa câu/chuyển động
- Đẩy lên Facebook Livestream (RTMP qua OBS)
- Test end-to-end thực tế trên stream

**Tiến độ tổng:**

| Hạng mục | Status |
|---------|--------|
| Video loop liên tục có tiếng | ✅ |
| AI reply bằng audio khi có comment | ✅ |
| Gen nhép môi Wav2Lip (async) | ✅ |
| Video pause/resume quanh audio AI | ✅ |
| Wav2Lip code hook vào TTS pipeline | ✅ |
| Ghép nhép môi khít vào video đang chạy | 🔄 |
| Sync frame-level audio + lipsync vào video | ⬜ |
| Logic chọn điểm chèn trong video | ⬜ |
| Đẩy lên Facebook Livestream | ⬜ |
| Test end-to-end thực tế | ⬜ |

**→ 5/10 tasks = 50% hoàn thành** (task đang làm tính ~50% → thực tế khoảng **55%**)

---

## [Success #3] — 2026-06-28 18h35 — Wav2Lip lip sync chính xác + blend mượt vào luồng video chính

### Tóm tắt (nguyên văn)

> **Đánh dấu success 3 thành công gồm có:**
>
> **Success 1:** Khi khách chat thì AI phản hồi lại bằng Audio tích tắc (chưa đến 1s)
>
> **Success 2:**
> - Phát video avatar liên tục có tiếng (loop, không ngắt)
> - Khi khách comment → AI reply bằng Audio (Edge-TTS giọng Hoài My) + Gen nhép môi (Wav2Lip)
> - Video dừng lại để nhường chỗ cho audio AI phát
> - Audio AI phát xong → video tự chạy tiếp
> - Wav2Lip xử lý async nền (~3-15s), không block pipeline
>
> **Success 3:**
> - Nhép môi chuẩn đúng câu chữ trên đoạn AUDIO OUTPUT + ghép cực mượt vào trong luồng video đang phát =)) ngon vãi (blend mượt vào luồng video chính) - Hiện đang đợi audio (<1s) => nhép môi (10-20s) xong mới phát chèn vào audio
>
> **Next steps:**
> Căn cho AI check xem sẽ ngưng video ở đâu để ghép vào đoạn hợp lý thay vì là đợi nhép môi xong thì ghép luôn.

### Mục tiêu đạt được

- **Nhép môi chuẩn đúng câu chữ trên đoạn AUDIO OUTPUT** — Wav2Lip sinh ra đúng khẩu hình tiếng Việt khớp với từng âm tiết AI nói
- **Blend cực mượt vào luồng video chính** — lipsync video chèn liền mạch vào giữa idle video loop, không giật, không cut đột ngột
- **Pipeline đồng bộ hoàn chỉnh:** audio (<1s) → nhép môi gen (10–20s) → lipsync video + audio phát khớp nhau
- **Nguyên tắc fallback:** khách không bao giờ nghe im lặng — nếu Wav2Lip fail, audio TTS vẫn phát qua channel riêng

### Luồng hoạt động mới (so với Success #2)

```
Khách comment
    ↓
AI think + TTS generate audio file (<1s)
    ↓
Wav2Lip available? YES → submit audio vào queue async
                         → SKIP phát audio ngay (tránh double audio)
    ↓
[10–20s Wav2Lip inference — background, không block pipeline]
    ↓
Wav2Lip xong → play_lipsync(video_with_embedded_audio)
    ↓
OpenCV window: dừng idle → phát lipsync video CÓ AUDIO khớp nhép môi
    ↓
Lipsync xong → idle video tiếp tục từ frame 0
```

### avatar/pipeline.py — on_audio_ready() trả về bool

**Thay đổi:**
- `on_audio_ready(audio_path) -> bool` — trả về `True` nếu Wav2Lip handle audio
- Khi `True`: caller bỏ qua Fay audio pipeline, tránh phát audio 2 lần (TTS ngay + lipsync video sau)
- Khi `False` (Wav2Lip không khả dụng): return False → caller tự phát audio bình thường

### core/fay_core.py — Skip audio pipeline khi Wav2Lip handle

**Thay đổi:**
- `_lipsync_handles_audio = False` — init ngay cạnh `result = None` (tránh UnboundLocalError mọi code path)
- Sau TTS xong: gọi `avatar_pipeline.on_audio_ready(result)`
- Nếu trả về `True` → **không** gọi `MyThread(__process_output_audio)` → audio chỉ đến từ lipsync video
- Nếu trả về `False` → gọi `__process_output_audio` bình thường như cũ

**Fix UnboundLocalError:**
- Variable `_lipsync_handles_audio` trước được init bên trong 3 lớp `if` lồng nhau
- Code path thứ 2 (chunked text output) không chạm assignment → `UnboundLocalError`
- Fix: đưa init lên `result = None` level — đảm bảo mọi branch đều có giá trị

### avatar/lip_sync.py — Fallback audio khi Wav2Lip fail

**Nguyên tắc:** khách không được biết là AI Livestream — không bao giờ để im lặng.

**Các trường hợp fallback mới:**
- `face_input` không tồn tại (chưa có file avatar) → `_fallback_play_audio(audio_path)`
- `_run_wav2lip()` trả về `False` (inference lỗi / timeout) → `_fallback_play_audio(audio_path)`

**`_fallback_play_audio(audio_path)`:**
- Dùng `pygame.mixer.Sound` (channel riêng) — không đụng idle video `.music` channel
- Block worker thread cho đến khi audio phát xong (`channel.get_busy()` polling)
- Auto-convert không phải `.wav` bằng `_extract_audio_wav()` (ffmpeg) trước khi play
- Try/except toàn bộ → nếu pygame cũng fail, log lỗi và tiếp tục (không crash)

### avatar/video_display.py — Fix 2 bugs sau khi speaking xong

**Bug 1: Video freeze sau khi lipsync kết thúc**
- Root cause: sau `_play_once()`, `_idle_cap` ở frame N (vị trí cũ). Idle audio restart từ 0.
  Audio-clock sync tính `gap = 0 - N = rất âm` → `return` mà không hiển thị frame → video đứng hình N/fps giây
- Fix: sau `SPEAKING → IDLE`, `self._idle_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)` reset về đầu

**Bug 2: Lipsync video không hiển thị nếu audio extract fail**
- Root cause: nếu `_extract_audio_wav()` trả về `None`, `pygame.get_pos()` = -1 ngay lập tức → `break` trước khi hiển thị frame nào
- Fix: `use_audio_sync = _pygame_available and wav is not None`
  - Nếu có audio → audio-clock-driven sync (như cũ)
  - Nếu không có audio → time-based playback (`time.sleep(frame_duration)` mỗi frame)

### avatar/Wav2Lip/inference.py — Fix ffmpeg path không tồn tại

**Vấn đề:** `imageio_ffmpeg.get_ffmpeg_exe()` trả về path nhưng file không tồn tại trên máy (chưa download / wrong version) → `WinError 2: The system cannot find the file specified` ở bước mux cuối (sau ~60 phút inference!)

**Fix:**
```python
import shutil as _shutil
try:
    import imageio_ffmpeg as _iio_ffmpeg
    _candidate = _iio_ffmpeg.get_ffmpeg_exe()
    _FFMPEG = _candidate if os.path.isfile(_candidate) else (_shutil.which('ffmpeg') or 'ffmpeg')
except Exception:
    _FFMPEG = _shutil.which('ffmpeg') or 'ffmpeg'
```
- Check `os.path.isfile()` trước khi dùng path từ imageio
- Fallback `shutil.which('ffmpeg')` tìm ffmpeg trong PATH (được inject bởi `lip_sync.py`)
- Đảm bảo mux step không bao giờ fail vì path

### llm/nlp_cognitive_stream.py — Dịch internal messages sang tiếng Việt

**Vấn đề:** Edge-TTS voice `vi-VN-HoaiMyNeural` không synthesize được tiếng Trung → TTS fail với `"No audio was received"` cho các internal status messages.

**Messages đã dịch:**
| Chinese (cũ) | Vietnamese (mới) |
|---|---|
| `等等，我再帮你核实一下…` | `Để Linh xác nhận lại thông tin cho bạn nhé…` |
| `我来帮你查一下，稍等…` | `Để mình kiểm tra giúp bạn, chờ chút nhé…` |
| `抱歉，处理结果时出了点问题。` | `Xin lỗi, có chút trục trặc khi xử lý kết quả.` |
| `抱歉，我现在太忙了...` | `Xin lỗi, mình đang bận quá, bạn thử lại sau nhé.` |
| `抱歉，我的大脑暂时开了小差...` | `Xin lỗi, mình gặp chút sự cố, bạn thử lại sau nhé.` |

### Next Steps

- **Logic thông minh chèn lipsync:** AI quyết định điểm dừng idle video hợp lý (cuối câu / giữa chuyển động nhẹ) thay vì ghép ngay khi gen xong
- **S4:** Auto-read comment Facebook Live (Selenium scraper)
- **S5:** OBS → RTMP → Facebook/TikTok Live stream

---

## [Success #2] — 2026-06-28 16h00 — Video loop + Audio A/V sync + Auto-fit window

### Mục tiêu đạt được
- Video avatar phát vòng lặp liên tục (IDLE mode)
- Khi AI trả lời: video dừng, audio phát
- Khi audio xong: video tiếp tục từ vị trí cũ
- Audio và video KHÔNG bị lệch nhau (audio-clock-driven sync)
- Cửa sổ tự co vừa màn hình desktop, user có thể kéo resize

### avatar/video_display.py — Refactor toàn bộ A/V sync

**Vấn đề cũ:**
- Audio (pygame) và video (time.sleep) chạy 2 đồng hồ độc lập
- `time.sleep(1/FPS)` không trừ thời gian render → drift tích lũy
- `cv2.waitKey(1)` bên ngoài loop thêm ~1-2ms/frame không được tính
- Config hardcode `FPS=25` nhưng video gốc là 30fps → video chậm hơn audio 17%

**Fix:**
- Thêm `_precise_sleep(frame_start, duration)`: tính thời gian còn lại sau xử lý frame, không sleep thừa
- Thêm audio-clock-driven sync cho IDLE mode:
  - `pygame.mixer.music.get_pos()` lấy vị trí audio chính xác (hardware clock)
  - Tính `target_frame = audio_pos_ms / 1000 * fps`
  - Nếu video chậm hơn audio → `cap.set(POS_FRAMES, target_frame)` skip bắt kịp
  - Nếu video nhanh hơn audio → sleep 1 frame chờ
- Thêm audio-clock-driven sync cho SPEAKING mode (`_play_once`): cùng cơ chế
- Video loop: khi hết video → `pygame.mixer.music.rewind()` + `play()` đồng bộ lại từ đầu

**Thêm `_fit_to_screen()`:**
- Dùng `tkinter` đọc screen resolution thực tế
- Scale window xuống 90% màn hình, giữ nguyên aspect ratio
- Không bao giờ upscale (scale cap ở 1.0)
- Ví dụ: video 1080×1920 trên màn hình 1536×960 → window 486×864

**Thêm letterbox `_resize()`:**
- Giữ aspect ratio khi resize frame
- Nếu tỷ lệ nguồn ≠ tỷ lệ đích → thêm viền đen (letterbox)
- Tránh stretch méo hình

### avatar/config.py — Auto-detect thay vì hardcode

- `WIDTH = None`, `HEIGHT = None`: tự detect từ video gốc lúc khởi động
- `FPS = 25`: chỉ là fallback khi không đọc được FPS từ video
- Video gốc 1080×1920 @ 30fps được detect tự động, không cần sửa config

### utils/config_util.py — Load .env + Fix embedding skip

**Load .env tự động:**
- Đọc `.env` ở thư mục gốc trước khi load `system.conf`
- Parse `KEY=VALUE`, bỏ qua comment `#` và dòng trống
- Dùng `os.environ.setdefault` → không override biến env đã có sẵn

**Đọc Gemini API key từ env:**
- Expand `%ENV_VAR%` và `${ENV_VAR}` trong `gpt_api_key`
- Fallback: `os.environ.get('GEMINI_API_KEY')` nếu `system.conf` để trống
- Kết quả: key chỉ cần đặt trong `.env`, không hardcode vào `system.conf`

**Fix embedding spam 400 error:**
- Trước: `embedding_api_base_url = embedding_base_url or gpt_base_url` → gọi Gemini `/embeddings` → 400
- Sau: chỉ enable embedding nếu `embedding_api_model` được cấu hình rõ
- Nếu model trống → `embedding_api_base_url = None` → skip API, dùng mock vector ngay
- Không còn spam log lỗi 400 mỗi request

**Fix BOM trong system.conf:**
- Đổi `encoding='UTF-8'` → `encoding='utf-8-sig'` khi đọc configparser
- `utf-8-sig` tự strip BOM `﻿` nếu có, không ảnh hưởng file không có BOM

### .env (mới)
- File template chứa API keys, không commit lên git
- `GEMINI_API_KEY=` — điền key Gemini tại đây
- Đã có trong `.gitignore`

---

## [Success #1] — 2026-06-28 15h00 — commit `4abd566`

### Mục tiêu đạt được
Khách chat → AI reply bằng **audio tiếng Việt** + **icon mấp máy miệng** góc trái màn hình.
Đây là lần đầu tiên pipeline hoạt động end-to-end: text input → LLM → TTS → audio phát + animation.

### Chi tiết kỹ thuật

**Persona & LLM (Vietnamese AI Sales Host):**
- `config.json`: thiết lập nhân vật **Linh** — AI sales host thương hiệu Dr.Bee Nhộng Ong Haircare
- `llm/nlp_cognitive_stream.py`: system prompt tiếng Việt — tư vấn bán hàng, xử lý objection, upsell combo 590K
- `qa.csv`: 16 cặp Q&A tiếng Việt về sản phẩm Dr.Bee (gội đầu, dưỡng tóc, bảng giá, thành phần)
- LLM backend: **Google Gemini 2.5 Flash** qua OpenAI-compatible endpoint

**TTS tiếng Việt (Edge-TTS):**
- `tts/tts_voice.py`: thêm 2 giọng Việt mới:
  - `Hoài My (vi-nữ)` — `vi-VN-HoaiMyNeural` — giọng nữ miền Nam
  - `Nam Minh (vi-nam)` — `vi-VN-NamMinhNeural` — giọng nam
- Miễn phí, không cần API key, độ trễ ~500ms

**Icon mấp máy miệng:**
- Fay mặc định có widget face animation ở góc trái màn hình (built-in)
- Khi TTS phát audio → widget tự động animate mấp máy theo biên độ âm thanh
- Không cần code thêm — chỉ cần TTS hoạt động đúng là icon chạy

**UI Việt hoá toàn bộ (Chinese → Vietnamese):**
- `gui/templates/index.html`: toàn bộ chat interface, placeholder, nhãn nút
- `gui/templates/setting.html`: trang cài đặt, labels, descriptions
- `gui/static/js/setting.js`: alerts, dialogs, confirm messages
- `gui/static/js/script.js`: comments trong code
- `gui/flask_server.py`: comments, docstrings, error messages

**Config & Tooling:**
- `system.conf.example`: template cấu hình với placeholder (không chứa key thật)
- `system.conf` + `verifier.json` → thêm vào `.gitignore` tránh lộ key
- `cache_data/config.json`: bản copy config cần thiết lúc runtime
- `START_DEMO.bat`: launcher Windows 1-click, check Python, in hướng dẫn
- `OBS_SETUP_GUIDE.md`: hướng dẫn kết nối OBS để stream lên Facebook/TikTok

### Pipeline hoàn chỉnh Success #1
```
Khách gõ comment vào chat UI (http://127.0.0.1:5000)
    ↓
Fay AI (Linh) xử lý qua Gemini 2.5 Flash
    ↓
Edge-TTS tổng hợp audio tiếng Việt (giọng Hoài My)
    ↓
Audio phát ra loa + Icon face ở góc trái mấp máy miệng theo âm thanh
```

---

## [Phase 1 Demo] — 2026-06-28 (cập nhật lần 2)

### AI Livestream Vietnamese Sales Host — Doctor Bee / Nhộng Ong Haircare

#### Added
- **Vietnamese TTS voices** (`tts/tts_voice.py`): Added `Hoài My (vi-nữ)` and `Nam Minh (vi-nam)` via Edge-TTS — no API key required, runs fully on CPU.
- **Vietnamese Sales Host system prompt** (`llm/nlp_cognitive_stream.py`): Auto-activates when `job` config contains "host", "livestream", or "bán hàng". Sales-optimized persona with call-to-action rules, urgency creation, and Vietnamese conversational style.
- **Vietnamese FAQ product script** (`qa.csv`): 8 pre-built Q&A pairs covering ship, pricing, quality, payment (COD/Momo/ZaloPay), warranty, and ordering flow — all in Vietnamese.
- **Doctor Bee product catalog** (`qa.csv`): Full product knowledge for Dr.Bee Nhộng Ong Haircare — ingredients, USPs, combos, pricing, and closing scripts for livestream sales.
- **`START_DEMO.bat`**: One-click Windows launcher with config validation and clear error messages.

#### Changed
- **`config.json`**: Switched persona from default Chinese AI companion to **Linh** — Vietnamese AI Livestream Sales Host for Doctor Bee brand.
- **`system.conf`**: Configured for Phase 1 demo stack — `tts_module=edge` (free, no key) + DeepSeek API LLM + web mode on port 5000.

#### UI Localization
- **`gui/templates/index.html`**: Toàn bộ giao diện chat dịch sang tiếng Việt (menu, placeholder, labels, dialogs).
- **`gui/templates/setting.html`**: Trang cài đặt dịch sang tiếng Việt (form labels, dropdowns, nút bấm).
- **`gui/static/js/setting.js`**: Tất cả thông báo, dialog confirm, alert dịch sang tiếng Việt.
- **`gui/static/js/script.js`**: Comments code dịch sang tiếng Việt.
- **`gui/flask_server.py`**: Comments, docstrings, error messages dịch sang tiếng Việt.

#### LLM Configuration
- **`system.conf`**: Chuyển từ DeepSeek sang **Google Gemini 2.5 Flash** (OpenAI-compatible endpoint) — nhanh hơn, ổn định hơn cho demo.
  - `gpt_base_url=https://generativelanguage.googleapis.com/v1beta/openai/`
  - `gpt_model_engine=gemini-2.5-flash`

#### Tech Stack (Phase 1)
| Component | Solution | Cost |
|-----------|----------|------|
| LLM | Google Gemini 2.5 Flash | Free tier |
| TTS | Edge-TTS (vi-VN-HoaiMyNeural) | Free |
| ASR | FunASR local / manual input | Free |
| Server | Flask port 5000 | CPU only |
| Demo | Browser + OBS screen capture | — |

---

## [Base] — Pre-2026-06-28

Original Fay framework — Chinese digital human companion with ASR/LLM/TTS pipeline.
See original README for setup instructions.
