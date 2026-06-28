# CHANGELOG

All notable changes to this project will be documented in this file.

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
