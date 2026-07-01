# High-Level Design — Luồng xử lý response

---

## Phase 0 — Luồng cơ bản: Comment → Text → Audio

Luồng gốc của Fay trước khi có avatar/lipsync. Khách comment → AI trả lời text → phát audio.

```
Khách comment (text / voice)
        │
        ▼
┌───────────────────┐
│   qa_service /    │  Routing: QnA tĩnh, persona, hay LLM?
│  llm_execution    │
└────────┬──────────┘
         │ LLM streaming (token by token)
         ▼
┌──────────────────────────────────────────┐
│            stream_manager                │
│                                          │
│  Token → gom thành câu hoàn chỉnh        │
│  (dấu câu: . ! ? … hoặc xuống dòng)     │
│                                          │
│  Tag từng câu:                           │
│    _<isfirst>  — câu đầu tiên            │
│    _<isend>    — câu cuối cùng           │
│    conv_id     — __<cid=xxx>__           │
│                                          │
│  SentenceCache (ring buffer)             │
│  listen() thread → execute() mỗi câu    │
└────────┬─────────────────────────────────┘
         │ Interact(username, sentence, is_first, is_end, conv_id)
         ▼
┌──────────────────────────────────────────┐
│             fay_core.say()               │
│                                          │
│  1. Clean text (emoji, tags, markdown)   │
│  2. Normalize (merge lines, spacing)     │
│  3. TTS cache check (SHA1 hash)          │
│  4. TTS engine → audio.wav              │
│  5. WebSocket → hiển thị text lên UI    │
│  6. Phát audio trực tiếp (pygame)        │
└──────────────────────────────────────────┘
```

**TTS engines được hỗ trợ**: Microsoft TTS / GPT-SoVITS / GPT-SoVITS v3 / Volcano TTS / Ali TTS

**Kết quả**: Khách thấy text trả lời trên UI + nghe audio response.

---

## Phase 1 — Luồng hiện tại: + Nhép môi + Chèn video lipsync

Mở rộng Phase 0: sau khi TTS xong, thay vì phát audio trực tiếp → đưa qua Wav2Lip để tạo video nhép môi, rồi chèn vào giữa luồng video idle đang chạy.

```
... (giống Phase 0 đến bước fay_core.say()) ...
         │
         │  audio.wav + is_end + conv_id
         ▼
┌──────────────────────────────────────────────────────────┐
│                  avatar/pipeline.py                      │
│                                                          │
│  Buffer audio theo conversation_id:                      │
│                                                          │
│    Câu 1 (is_end=False) → buffer[conv_id] += [audio1]   │
│    Câu 2 (is_end=False) → buffer[conv_id] += [audio2]   │
│    Câu 3 (is_end=True)  → drain buffer                  │
│                        → ffmpeg concat → merged.wav     │
│                        → lip_sync.submit(merged.wav)    │
│                                                          │
│  Mục đích: tránh Wav2Lip chạy 3 lần → avatar nhép môi  │
│  bị tách đoạn. Gộp thành 1 job duy nhất.               │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│                  avatar/lip_sync.py                      │
│                                                          │
│  Worker thread (queue FIFO):                             │
│                                                          │
│    Wav2Lip inference:                                    │
│      input:  merged.wav  +  avatar_idle.mp4             │
│      output: lipsync_TIMESTAMP.mp4                      │
│      flags:  --resize_factor 4  --nosmooth              │
│                                                          │
│    CPU: ~60-90s  |  GPU: ~3-5s                          │
│                                                          │
│    Fail → fallback: phát audio trực tiếp (pygame)       │
└────────┬─────────────────────────────────────────────────┘
         │  lipsync_TIMESTAMP.mp4
         ▼
┌──────────────────────────────────────────────────────────┐
│               avatar/video_display.py                    │
│                                                          │
│  ┌─────────────────────────────────────────────────┐    │
│  │  IDLE mode (liên tục)                           │    │
│  │  Loop avatar_idle.mp4 + audio track             │    │
│  │  Audio-clock sync: skip/wait frame theo audio   │    │
│  └─────────────────────────────────────────────────┘    │
│              ↕  switch                                   │
│  ┌─────────────────────────────────────────────────┐    │
│  │  SPEAKING mode                                  │    │
│  │  Play lipsync_TIMESTAMP.mp4 một lần             │    │
│  │  Audio-clock sync                               │    │
│  │  Xong → reset idle về frame 0 → IDLE           │    │
│  └─────────────────────────────────────────────────┘    │
│                                                          │
│  Chèn điểm đẹp nhờ golden frame:                        │
│    play_lipsync() → set _pending (không switch ngay)    │
│    Mỗi frame: kiểm tra _at_golden_frame()               │
│      True  → switch SPEAKING                            │
│      False → tiếp tục IDLE                             │
│    Timeout 3s → force switch (fail-safe)                │
└────────┬─────────────────────────────────────────────────┘
         │  startup (1 lần)
         ▼
┌──────────────────────────────────────────────────────────┐
│               avatar/stillness.py                        │
│                                                          │
│  Pre-compute golden frames (background thread):          │
│    1. Optical flow (Farneback) → motion_score/frame     │
│    2. _audio.wav RMS → silence_mask/frame               │
│    3. Golden = motion < 1.5px AND silence RMS < 5%      │
│    → cache list[int] frame indices                      │
│                                                          │
│  Mục đích: chèn lipsync vào đúng lúc avatar đứng yên,  │
│  tránh cắt đột ngột giữa chuyển động.                   │
└──────────────────────────────────────────────────────────┘
```

---

## Timing thực tế (CPU, từ log)

```
t=0s      Khách gửi message
t=0.9s    TTS câu 1 xong → buffer
t=5.2s    TTS câu 2 xong → buffer  (is_end=True)
           → ffmpeg concat → merged.wav
           → submit Wav2Lip
t=~75s    Wav2Lip xong → video_display.play_lipsync()
           → tìm golden frame → switch SPEAKING
t=~75s+   Avatar nhép môi toàn bộ response (1 video liên tục)
```

> **Bottleneck**: Wav2Lip trên CPU ~60-90s. Trên GPU giảm xuống ~3-5s.

---

## So sánh Phase 0 vs Phase 1

| | Phase 0 | Phase 1 |
|--|---------|---------|
| Output | Text UI + Audio | Text UI + Lipsync video |
| Audio | Phát ngay sau TTS | Buffer đến is_end → concat → Wav2Lip |
| Latency đến âm thanh | ~1-2s | ~60-90s (CPU) / ~5s (GPU) |
| Avatar | Không có / ảnh tĩnh | Video idle loop + nhép môi |
| Điểm chèn video | N/A | Golden frame (tĩnh + lặng) |

---

## Files liên quan

| File | Phase | Vai trò |
|------|-------|---------|
| `core/stream_manager.py` | 0+1 | Gom token → câu, tag is_first/is_end |
| `core/fay_core.py` | 0+1 | TTS, cache, routing output |
| `avatar/pipeline.py` | 1 | Buffer audio per conv, ffmpeg concat |
| `avatar/lip_sync.py` | 1 | Wav2Lip worker queue |
| `avatar/video_display.py` | 1 | Display IDLE/SPEAKING, golden frame |
| `avatar/stillness.py` | 1 | Pre-compute golden frames |
| `avatar/config.py` | 1 | Paths: idle video, checkpoint, output |
