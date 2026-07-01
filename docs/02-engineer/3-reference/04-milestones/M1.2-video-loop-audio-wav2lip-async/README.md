# M1.2 — Video avatar loop liên tục + Audio AI + Wav2Lip async

**Trạng thái:** ✅ Hoàn thành

## Mục tiêu

- Video idle phát **liên tục có tiếng** (loop, không ngắt)
- Khi có comment → AI reply bằng **Audio Edge-TTS** + gen **Wav2Lip** ở nền
- Video **dừng nhường chỗ** cho audio AI → audio xong → **video chạy tiếp**
- Wav2Lip xử lý **async** (~3–15s), **không block** pipeline phát audio

## Kiến trúc 2 mode

```
[IDLE]     avatar_idle.mp4 → loop liên tục, audio-clock sync
               ↓ comment đến
[SPEAKING] stop idle → phát audio TTS trực tiếp (hoặc lipsync video nếu đã cache)
               ↓ xong
[IDLE]     video loop tiếp từ frame 0

           (song song, không block)
[Wav2Lip BG] worker thread → chạy Wav2Lip → enqueue lipsync video vào queue
```

## Audio-clock sync (idle loop)

```python
audio_pos_ms = pygame.mixer.music.get_pos()
target_frame = int((audio_pos_ms / 1000.0) * fps)
# skip frame nếu video tụt hậu audio, wait nếu video đi trước
```

## Wav2Lip async flow

```
lip_sync.submit(audio_path)
    → _job_queue.put(job)
    → _worker_loop() (background thread)
        → _run_wav2lip(face, audio, output)
        → VideoDisplay._lipsync_queue.put(output_path)
```

## Files

| File | Vai trò |
|---|---|
| `avatar/video_display.py` | 2-mode display, audio sync, queue |
| `avatar/lip_sync.py` | Wav2Lip worker thread |
| `avatar/pipeline.py` | Khởi động + routing audio → Wav2Lip |
| `avatar/config.py` | Path video idle, FPS, kích thước cửa sổ |
