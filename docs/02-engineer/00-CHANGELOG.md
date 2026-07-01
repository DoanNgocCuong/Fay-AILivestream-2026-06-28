# CHANGELOG — Dr.Bee AI Livestream Host (Fay)

---

## [2026-07-01] Fill Phrase System + Avatar Pipeline Overhaul

### Tổng quan
Triển khai **fill phrase system** để avatar phản hồi lập tức khi có comment — không còn im lặng chờ Wav2Lip (60-120s). Song song đó, cải tiến toàn bộ avatar pipeline và bổ sung loạt tính năng mới cho hệ thống livestream.

---

### 1. Fill Phrase System (`avatar/fill_phrases.py` — file mới)

**Vấn đề giải quyết:** Khi khách comment, avatar mất 60-120s xử lý Wav2Lip mới có video nhép môi → viewer thấy im lặng, không tự nhiên.

**Giải pháp:** Pre-compute 2 câu chuyển tiếp cố định ở startup, cache ra disk, play tức thì khi cần.

**Chi tiết kỹ thuật:**
- **2 fill phrase:**
  - `thinking`: *"Linh thấy anh chị có comment. Anh chị đợi Linh chút, Linh sẽ trả lời anh chị ạ."* — phát **ngay lập tức** khi comment đến
  - `closing`: *"Linh xin phép quay lại tư vấn sản phẩm tiếp ạ."* — phát sau khi main response xong
- **Hash-based cache invalidation:** mỗi file `.mp4` đi kèm file `.hash` (md5 của text + voice). Nếu text thay đổi → tự xóa cache cũ, recompute
- **Cache location:** `avatar/assets/fill_cache/fill_{key}.mp4/.wav/.hash`
- **Thread-safe:** `_ready_event` (threading.Event) gate việc khởi động VideoDisplay
- **API:** `precompute_async()`, `wait_until_ready()`, `play_thinking()`, `get_closing_path()`

---

### 2. Avatar Pipeline — Delayed Start (`avatar/pipeline.py`)

**Thay đổi:** `pipeline.start()` không còn khởi động VideoDisplay ngay lập tức.

**Flow mới:**
```
pipeline.start()
  → fill_phrases.precompute_async()   # chạy ở background thread
  → _delayed_start() thread           # chờ fill phrases sẵn sàng (tối đa 300s)
      → get_display().start()         # VideoDisplay chỉ khởi động SAU KHI fill phrases xong
```

**Tại sao:** Đảm bảo `fill_thinking.mp4` và `fill_closing.mp4` đã có trong cache trước khi livestream bắt đầu nhận comment.

**Thêm mới:**
- `on_audio_ready()` giờ nhận `is_end: bool` và `conversation_id: str` — hỗ trợ buffering mode
- `flush_buffer()` — no-op placeholder cho streaming mode
- Tích hợp **Sync.so** cloud lip sync: nếu `syncso_api_key` được cấu hình → ưu tiên dùng Sync.so thay Wav2Lip local

---

### 3. Lip Sync Buffering Mode (`avatar/lip_sync.py`)

**Thay đổi lớn nhất:** Từ "submit từng chunk ngay" → **gom toàn bộ audio của 1 conversation, concatenate thành 1 WAV dài, chạy Wav2Lip 1 lần** → video liền mạch không bị giật.

**API mới:**
```python
submit(audio_path, is_last=False, conversation_id="default")
  # is_last=False → gom vào buffer
  # is_last=True  → concatenate + chạy Wav2Lip 1 lần duy nhất
```

**WAV concatenation:** `_concatenate_wavs(list[str], output_path)` — dùng `wave` stdlib, không cần ffmpeg, handle khác sample rate/channels bằng fallback.

**Closing phrase:** Sau khi Wav2Lip xong (is_last=True) → tự động enqueue `fill_closing.mp4` vào VideoDisplay queue.

---

### 4. Video Display — Queue + Golden Frame (`avatar/video_display.py`)

**Thêm:**
- `_lipsync_queue: queue.Queue` — videos play theo thứ tự submit (FIFO)
- `play_lipsync(video_path, follow_up_path=None)` — enqueue video + optional follow-up
- `_pending_lipsync_path` + golden frame wait — chờ idle video đến "điểm đứng đẹp" rồi mới chuyển sang SPEAKING (tối đa 3s timeout)
- **OBS Virtual Camera:** `pyvirtualcam` integration — push mỗi frame lên OBS Virtual Camera khi `OBS_VIRTUAL_CAM=True` trong config

---

### 5. Stillness Module (`avatar/stillness.py` — file mới)

Pre-compute **golden frames** từ idle video: frame có motion thấp (optical flow) + trùng với khoảng lặng audio.
- `precompute_async(video_path)` — chạy background sau khi VideoDisplay khởi động
- `next_golden_frame(video_path, current, total)` — trả về frame index gần nhất để switch vào SPEAKING
- Cache kết quả vào memory (không cần recompute lần 2)

---

### 6. Sync.so Cloud Lip Sync (`avatar/syncso_lipsync.py` — file mới)

Tích hợp [Sync.so API](https://docs.sync.so/) như **alternative backend** cho Wav2Lip.

**Flow:**
```
audio_path + avatar_video → POST /v2/generate → poll status → download .mp4
```

**Config:**
```ini
# system.conf
syncso_api_key=your_api_key_here
syncso_avatar_video=./avatar/assets/avatar_idle.mp4
```

**Ưu tiên:** Nếu `syncso_api_key` có trong config → dùng Sync.so; nếu không → fallback về Wav2Lip local.

---

### 7. Knowledge Base — Direct Inject vào System Prompt (`llm/nlp_cognitive_stream.py`)

**Vấn đề:** Gemini không biết thông tin sản phẩm Dr.Bee → trả lời sai hoặc bịa.

**Giải pháp:** Inject thẳng file `data/data_san_pham.md` vào system prompt — **không dùng RAG/embedding**.

**Lý do chọn direct inject thay vì RAG:**
| Tiêu chí | Direct Inject | RAG/Embedding |
|---|---|---|
| File size | ~3.000 tokens (0,3% context 1M) | — |
| Retrieval miss | Không có | Có thể miss |
| Latency | 0ms overhead | +100-500ms |
| Bug surface | Thấp | Cao |

**Code:**
```python
_kb_path = "data/data_san_pham.md"
system_prompt += f"\n\n**KIẾN THỨC SẢN PHẨM DR.BEE**\n{_kb_content}\n"
```

**Nội dung `data_san_pham.md` bao gồm:**
- So sánh Nhộng Ong vs Clear/Sunsilk/Pantene/Dove
- Thành phần: tinh chất Nhộng Ong, Nhân Sâm, Collagen, Vitamin B
- Tác hại SLS/Paraben/Silicone
- Bảng giá: 280K/hộp, Combo 599K, Combo 1.100K
- Cam kết hoàn tiền 100% sau 15 ngày

---

### 8. System Prompt Livestream — 5 Loại Comment (`llm/nlp_cognitive_stream.py`)

Cải tiến toàn bộ system prompt: từ chatbot generic → **AI host livestream bán hàng** có kịch bản rõ ràng.

**5 loại comment + cách reply:**

| Loại | Trigger | Cách reply |
|---|---|---|
| Loại 1 | Chào hỏi / vào live | Chào ngắn (1 câu) + pivot sản phẩm + CTA |
| Loại 2 | Hỏi giá / hỏi sản phẩm | Tên SP + lợi ích + giá + urgency + CTA SĐT |
| Loại 3 | Quan tâm / thích | Xác nhận cảm xúc + khan hiếm + thúc SĐT |
| Loại 4 | Phàn nàn / nghi ngờ giá | Không tranh cãi + social proof + cam kết + CTA thử |
| Loại 5 | Off-topic / linh tinh | Vui vẻ ngắn + kéo về sản phẩm |

**Quy tắc bất biến:**
1. LUÔN trả lời bằng tiếng Việt
2. Nói như đang trực tiếp trên sóng — không viết như chatbot
3. KHÔNG dùng gạch đầu dòng, KHÔNG liệt kê kiểu báo cáo
4. KHÔNG bịa thông tin — nếu không chắc thì "để Linh check lại"

---

### 9. Fay Core — Thinking Phrase tại Comment (`core/fay_core.py`)

Thêm trigger `fill_phrases.play_thinking()` **ngay khi comment đến** — độc lập với Wav2Lip pipeline:

```python
# Phát thinking phrase ngay khi nhận comment — độc lập với Wav2Lip
try:
    from avatar import fill_phrases as _fp
    _fp.play_thinking()
except Exception:
    pass
```

**Thêm:** `on_audio_ready()` giờ pass `is_end` và `conversation_id` sang avatar pipeline để hỗ trợ buffering mode.

---

### 10. Live Comment Service (`core/live_comment_service.py`, `facebook_reader.py`, `tiktok_reader.py` — file mới)

Dịch vụ tích hợp đọc comment từ **Facebook Live** và **TikTok Live**.

- Priority queue: real comment > proactive monologue
- Push vào Fay AI queue qua WebSocket `ws://localhost:10003`
- Config qua env: `LIVE_FB_URL`, `LIVE_TIKTOK_ID`, `LIVE_COMMENT_ENABLED`

---

### 11. ElevenLabs TTS (`tts/elevenlabs_tts.py` — file mới)

Alternative TTS backend bên cạnh Edge-TTS.

**Config:**
```ini
# system.conf
elevenlabs_api_key=your_key
elevenlabs_voice_id=your_voice_id
elevenlabs_model=eleven_multilingual_v2
```

---

### 12. OBS / Avatar Config (`avatar/config.py`, `utils/config_util.py`)

Thêm các config mới:
```python
OBS_VIRTUAL_CAM = False       # push frame lên OBS Virtual Camera
OBS_CAM_WIDTH   = 1280
OBS_CAM_HEIGHT  = 720
OBS_CAM_FPS     = 25
```

Config từ `system.conf`:
- `elevenlabs_api_key`, `elevenlabs_voice_id`, `elevenlabs_model`
- `syncso_api_key`, `syncso_avatar_video`

---

### 13. Bug Fixes & Log Cleanup

| File | Fix |
|---|---|
| `avatar/lip_sync.py` | Xóa param `is_first` — không còn dùng |
| `avatar/video_display.py` | Thêm `follow_up_path` vào `play_lipsync()` |
| `core/qa_service.py` | Dịch log message từ tiếng Trung → tiếng Việt |
| `llm/nlp_cognitive_stream.py` | Thêm traceback logging cho LLM error, cải thiện greeting detection |

---

### Files thay đổi

| File | Trạng thái | Mô tả |
|---|---|---|
| `avatar/fill_phrases.py` | **Mới** | Fill phrase pre-compute + cache system |
| `avatar/stillness.py` | **Mới** | Golden frame pre-computation |
| `avatar/syncso_lipsync.py` | **Mới** | Sync.so cloud lip sync integration |
| `core/live_comment_service.py` | **Mới** | Live comment reader service |
| `core/facebook_reader.py` | **Mới** | Facebook Live comment reader |
| `core/tiktok_reader.py` | **Mới** | TikTok Live comment reader |
| `tts/elevenlabs_tts.py` | **Mới** | ElevenLabs TTS backend |
| `avatar/pipeline.py` | Sửa | Delayed start + buffering mode + Sync.so routing |
| `avatar/lip_sync.py` | Sửa | Buffering mode — concat all chunks before Wav2Lip |
| `avatar/video_display.py` | Sửa | Queue-based play + golden frame wait + OBS vcam |
| `avatar/config.py` | Sửa | OBS virtual camera config |
| `core/fay_core.py` | Sửa | play_thinking() trigger + avatar buffering |
| `llm/nlp_cognitive_stream.py` | Sửa | KB inject + livestream system prompt |
| `utils/config_util.py` | Sửa | ElevenLabs + Sync.so config keys |
| `data/data_san_pham.md` | **Mới** | Knowledge base sản phẩm Dr.Bee |

---

## [2026-06-29] Lipsync Research & Phase 1 Documentation

- Research 3 giải pháp MECE cho lipsync insertion point
- Đánh giá model landscape: Wav2Lip, SadTalker, MuseTalk, Sync.so
- Phase 1 implementation record: Success #1 (video loop), #2 (A/V sync), #3 (Wav2Lip)

## [2026-06-28] Knowledge Base Inject + Wav2Lip Integration

- `feat`: inject `data_san_pham.md` vào system prompt trực tiếp (commit `d07a4a6`)
- `feat`: Wav2Lip lip sync — install + compatibility patches (commit `a7ada5f`)
- `fix`: fallback phát audio trực tiếp khi Wav2Lip fail (commit `88da534`)
- `fix`: Video display 2 bugs sau speaking mode (commit `0d49c6a`)
- `fix`: Dịch log messages từ tiếng Trung → tiếng Việt (commit `0e1ec24c`)
