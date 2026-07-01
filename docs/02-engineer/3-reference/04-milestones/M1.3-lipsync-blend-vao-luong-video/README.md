# M1.3 — Nhép môi chuẩn + blend mượt vào luồng video

**Trạng thái:** ✅ Hoàn thành

## Mục tiêu

- Lipsync **đúng câu chữ** với audio output (Wav2Lip inference)
- Video lipsync **ghép mượt** vào luồng idle — không giật, không đứng hình
- Flow: chờ audio (< 1s) → Wav2Lip async (10–20s) → chèn vào **điểm đứng đẹp**

## Vấn đề cũ

Switch từ idle sang lipsync ở **frame ngẫu nhiên** → avatar đang mở miệng/nghiêng đầu bị cắt ngang → giật hình rõ.

## Giải pháp: Golden Frame Wait

`avatar/stillness.py` pre-compute **golden frames** = frame có motion thấp (optical flow).

```python
# VideoDisplay._run loop
if pending_path and mode == _MODE_IDLE:
    timed_out = (time.perf_counter() - pending_since) > 3.0   # max 3s
    at_golden = self._at_golden_frame()
    if at_golden or timed_out:
        self._mode = _MODE_SPEAKING   # switch tại điểm đẹp
```

## Queue + Follow-up

```python
play_lipsync(main_video, follow_up_path=closing_video)
    → queue.put(main_video)
    → queue.put(closing_video)   # tự play ngay sau khi main xong
```

## Kết quả

| Trước | Sau |
|---|---|
| Switch ngay (frame ngẫu nhiên) | Chờ frame tĩnh (≤ 3s) |
| Giật hình rõ | Transition tự nhiên |
| Không có closing phrase | Tự enqueue `fill_closing.mp4` sau main response |

## Files

| File | Vai trò |
|---|---|
| `avatar/stillness.py` | Golden frame pre-compute (optical flow) |
| `avatar/video_display.py` | `_at_golden_frame()` + `_GOLDEN_WAIT_TIMEOUT` |
| `avatar/lip_sync.py` | Trigger closing phrase sau Wav2Lip |
| `avatar/fill_phrases.py` | Cache `fill_closing.mp4` |
