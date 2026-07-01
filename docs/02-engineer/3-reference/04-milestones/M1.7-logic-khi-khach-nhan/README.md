# M1.7 — Logic khi khách nhắn (Comment Handling Pipeline)

**Trạng thái:** ✅ Core logic xong / 🔄 Fill phrase + Live reader đang hoàn thiện

## Mục tiêu

Toàn bộ luồng xử lý khi khách gửi comment/chat lên livestream — từ lúc nhận tin đến lúc avatar phát xong câu trả lời.

## Full Pipeline

```
[Viewer comment]
      ↓
[Live Comment Service]      core/live_comment_service.py
  FacebookLiveReader / TikTokLiveReader
  → priority queue (real comment > monologue)
  → push vào Fay AI queue
      ↓
[fay_core.py nhận interact]
  1. play_thinking()         → fill_thinking.mp4 phát NGAY (có nhép môi)
  2. latency_tracker.start() → bắt đầu đo thời gian
      ↓
[LLM (Gemini streaming)]
  → stream token → sentence split
      ↓
[TTS per sentence (Edge-TTS)]
  → audio chunk
  → phát audio ngay (< 1s)
  → on_audio_ready(chunk, is_end=False) → buffer vào lip_sync
      ↓
[is_end=True — câu cuối]
  → on_audio_ready("", is_end=True) → flush buffer
  → lip_sync concat + Wav2Lip → lipsync video
      ↓
[VideoDisplay]
  → chờ golden frame
  → play lipsync video
  → play fill_closing.mp4
  → return IDLE
```

## Fill Phrase System (xử lý khoảng trống 10–20s chờ Wav2Lip)

| Phrase | Thời điểm phát | File |
|---|---|---|
| `thinking` | Ngay khi nhận comment (< 100ms) | `fill_thinking.mp4` |
| `closing` | Sau khi main response xong | `fill_closing.mp4` |

Pre-compute lúc startup, cache ra disk với hash-based invalidation.

```python
# fay_core.py — trigger ngay khi nhận comment
from avatar import fill_phrases as _fp
_fp.play_thinking()   # non-blocking, < 1ms
```

## Logic phân loại comment

`nlp_cognitive_stream.py` phân loại tự động qua system prompt:

| Loại | Trigger | Cách reply |
|---|---|---|
| Loại 1 | Chào hỏi / vào live | Chào ngắn + pivot sản phẩm + CTA |
| Loại 2 | Hỏi giá / hỏi sản phẩm | Tên SP + lợi ích + giá + urgency + CTA SĐT |
| Loại 3 | Quan tâm / thích | Xác nhận + khan hiếm + thúc SĐT |
| Loại 4 | Phàn nàn / nghi ngờ giá | Không tranh cãi + social proof + cam kết |
| Loại 5 | Off-topic / linh tinh | Vui vẻ ngắn + kéo về sản phẩm |

## Greeting detection (bỏ qua Wav2Lip)

Câu chào ngắn (< 10 ký tự hoặc thuộc `_GREETING_PATTERNS`) → trả lời ngay bằng TTS thuần, không chạy Wav2Lip (tiết kiệm 10–20s).

## Latency tracking

`utils/latency_tracker.py` đo từng bước:
- `start(conv_id, msg)` → lúc nhận comment
- `step(conv_id, label)` → sau mỗi milestone (TTS xong, Wav2Lip xong...)
- Log ra để phân tích bottleneck

## Files

| File | Vai trò |
|---|---|
| `core/live_comment_service.py` | Đọc comment từ Facebook/TikTok Live |
| `core/facebook_reader.py` | Facebook Live comment reader |
| `core/tiktok_reader.py` | TikTok Live comment reader |
| `core/fay_core.py` | Điều phối toàn bộ pipeline |
| `avatar/fill_phrases.py` | Thinking + closing phrase cache |
| `utils/latency_tracker.py` | Đo latency từng bước |
| `llm/nlp_cognitive_stream.py` | LLM + phân loại comment |
