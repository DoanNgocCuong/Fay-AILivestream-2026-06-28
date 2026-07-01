
## Luồng hiện tại (sau tất cả các fix)

---

### Startup

```
main.py start
  → pipeline.start()
      → VideoDisplay.start()          # OpenCV window chạy nền
      → fill_phrases.precompute_async()  # Thread nền: TTS + Wav2Lip cho 2 phrase
          → fill_thinking.wav + fill_thinking.mp4  (~60-120s lần đầu)
          → fill_closing.wav  + fill_closing.mp4   (~60-120s lần đầu)
          → Lần 2+: load từ disk cache ngay (<1s)
  → stillness.precompute_async()      # Thread nền: tính golden frames (~46s)
```

---

### Khi khách comment

```
fay_core nhận comment
  │
  ├─ fill_phrases.play_thinking()
  │     ├─ Nếu fill_thinking.mp4 đã cache → VideoDisplay.play_lipsync(thinking.mp4)
  │     │     → avatar chuyển IDLE → SPEAKING → phát thinking video (có nhép môi)
  │     │     → xong → về IDLE
  │     └─ Nếu chưa cache → log "Chua san sang", bỏ qua
  │
  └─ LLM xử lý (DeepSeek/Gemini)
        → streaming text ra từng câu
        → mỗi câu → TTS (Edge-TTS, ~500-800ms)
              → on_audio_ready(audio_path, is_end)
                    ├─ return False  → fay_core phát TTS audio NGAY QUA LẠOA regular path
                    └─ lip_sync.submit(audio_path, is_last=is_end)  [ASYNC, fire-and-forget]
                          → Wav2Lip queue (~60-120s per job)
```

---

### Wav2Lip worker (thread nền, xử lý từng job)

```
_worker_loop()
  │
  ├─ [Buoc 1/3] Wav2Lip render: audio → lipsync video (~60-120s)
  │
  ├─ [Buoc 2/3] Xong → VideoDisplay.play_lipsync(output.mp4, follow_up=closing.mp4)
  │     → avatar: IDLE → golden frame → SPEAKING
  │     → phát output.mp4 (lipsync chính, CÓ audio — replay lần 2)
  │     → phát closing.mp4 ngay sau (nếu đã cache)
  │     → về IDLE
  │
  └─ [Buoc 3/3] Log kết quả
```

---

### VideoDisplay states

```
IDLE ──────────────────────────────────────────────────────┐
  loop background video + audio                            │
  chờ golden frame (avatar đứng yên)                       │
  khi có pending_lipsync + ở golden frame → chuyển SPEAKING│
                                                            │
SPEAKING ───────────────────────────────────────────────────┘
  _play_once(video) → audio-clock sync → frame by frame
  xong → play follow_up nếu có
  xong → về IDLE
```

---

### Vấn đề còn tồn tại

| Vấn đề                                            | Nguyên nhân                                                       |
| ---------------------------------------------------- | ------------------------------------------------------------------- |
| Thinking phrase phát 2 lần audio ngay sau TTS xong | TTS audio phát ngay + Wav2Lip của thinking phrase cũng có audio |
| Lipsync chính phát audio lần 2 sau 60-120s        | User đã nghe rồi, nghe lại lần nữa khi video chạy            |
| Thinking chưa sẵn sàng lần đầu                 | Wav2Lip pre-compute nền chưa xong khi user comment ngay           |
