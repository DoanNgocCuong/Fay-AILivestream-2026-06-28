# M1.1 — Audio phản hồi dưới 1 giây

**Trạng thái:** ✅ Hoàn thành

## Mục tiêu

Khi khách comment, AI phát âm thanh trả lời trong vòng **< 1 giây** — không chờ LLM generate xong toàn bộ câu trả lời.

## Vấn đề ban đầu

Pipeline cũ: LLM generate toàn bộ → TTS cả đoạn → phát audio
→ Latency: **3–8 giây** từ lúc khách gửi đến lúc nghe thấy tiếng.

## Giải pháp: Streaming TTS theo câu

```
LLM stream token → buffer → cắt tại dấu câu → TTS câu đó ngay → phát
                                  ↓ song song
                             câu tiếp theo được TTS trong khi câu trước đang phát
```

1. Gemini Streaming API trả token realtime
2. `nlp_cognitive_stream.py` buffer token, phát hiện điểm cắt an toàn
3. Mỗi câu đủ → gọi Edge-TTS ngay → phát chunk đó
4. Câu tiếp theo xử lý song song

**Kết quả đo:** Chunk âm thanh đầu tiên phát trong **0.3–0.8s**.

## Điểm cắt câu an toàn (`_find_safe_split_point`)

Bỏ qua các dấu chấm không phải kết câu:
- Dấu chấm thập phân: `1.5`, `2.3`
- Tên thương hiệu: `Dr.Bee`
- Dấu chấm lửng chưa đủ: `..`

## Files

| File | Vai trò |
|---|---|
| `llm/nlp_cognitive_stream.py` | LLM streaming + `_find_safe_split_point()` |
| `tts/edge_tts_speech.py` | Edge-TTS wrapper (`vi-VN-HoaiMyNeural`) |
| `core/fay_core.py` | Điều phối audio playback per chunk |
