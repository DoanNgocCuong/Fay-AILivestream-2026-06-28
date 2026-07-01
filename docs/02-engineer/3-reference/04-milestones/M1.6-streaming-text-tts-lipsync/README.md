# M1.6 — Streaming: Text → TTS → Lipsync

**Trạng thái:** 🔄 Partial (TTS streaming ✅ / Per-sentence lipsync streaming ⏳)

## Mục tiêu

Thay pipeline blocking:
```
[Cũ] Text đầy đủ → TTS toàn bộ → chờ xong → Wav2Lip → phát
```

Thành pipeline streaming hoàn toàn:
```
[Mới] Token LLM → buffer câu → TTS câu → phát ngay → Wav2Lip câu → lipsync câu
```

Viewer nghe tiếng **< 1s**, thấy nhép môi **câu đầu trong 10–20s**, không phải chờ cả đoạn.

## Trạng thái từng bước

### ✅ Bước 1: Streaming Text → TTS (xong)

```
LLM stream token
  → _find_safe_split_point() → cắt câu
  → edge_tts(câu) → audio chunk
  → phát ngay lập tức
  → câu tiếp theo TTS song song
```

Latency chunk đầu: **0.3–0.8s**

### ✅ Bước 2: Audio buffering (xong)

Gom tất cả chunks → concat 1 WAV → Wav2Lip 1 lần → 1 video liền mạch:

```python
# lip_sync.py
submit(audio, is_last=False)  # gom vào buffer
submit(audio, is_last=True)   # concat + Wav2Lip
```

### ⏳ Bước 3: Per-sentence Wav2Lip streaming (chưa làm)

Mỗi câu TTS xong → Wav2Lip ngay (song song với câu tiếp đang TTS):

```
Câu 1 → TTS → audio1 → Wav2Lip(audio1) → lipsync1.mp4 → queue
Câu 2 → TTS → audio2 → Wav2Lip(audio2) → lipsync2.mp4 → queue
...
VideoDisplay: play lipsync1 → lipsync2 → ... seamless
```

**Thách thức kỹ thuật:**
- Wav2Lip cold start ~3s lần đầu → câu 1 bị delay
- Seamless transition giữa các lipsync segments (golden frame tại cuối mỗi segment)
- Audio sync: segment N+1 bắt đầu đúng lúc N kết thúc

## Giải pháp thay thế: Sync.so

`avatar/syncso_lipsync.py` — cloud API, 2–5s thay vì 10–20s Wav2Lip local.

```ini
# system.conf
syncso_api_key=your_key
syncso_avatar_video=./avatar/assets/avatar_idle.mp4
```

Nếu key có → ưu tiên Sync.so; không có → fallback Wav2Lip local.

## Files

| File | Vai trò |
|---|---|
| `llm/nlp_cognitive_stream.py` | LLM streaming + sentence split |
| `avatar/lip_sync.py` | Audio buffer + Wav2Lip worker |
| `avatar/syncso_lipsync.py` | Cloud lip sync alternative |
| `avatar/video_display.py` | Queue-based sequential playback |
