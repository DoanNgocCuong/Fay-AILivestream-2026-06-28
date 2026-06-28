# CHANGELOG

All notable changes to this project will be documented in this file.

---

## [Success #2] — 2026-06-28 — Video loop + Audio A/V sync + Auto-fit window

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

## [Success #1] — 2026-06-28 — commit `4abd566`

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
