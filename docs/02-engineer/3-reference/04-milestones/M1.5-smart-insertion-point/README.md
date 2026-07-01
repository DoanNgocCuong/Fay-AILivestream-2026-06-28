# M1.5 — Smart Insertion Point: AI chọn điểm dừng hợp lý để ghép lipsync

**Trạng thái:** ✅ Hoàn thành (golden frame approach)

## Mục tiêu

Không ghép lipsync vào **frame ngẫu nhiên** khi Wav2Lip xong → hệ thống tự tìm **điểm dừng đẹp nhất** trong idle video để chèn vào.

## Các hướng đã đánh giá

| Hướng | Ý tưởng | Kết quả |
|---|---|---|
| LLM decide | Hỏi LLM timestamp nên chèn vào đâu | ❌ Không khả thi — LLM không biết nội dung video |
| Scene cut detection | Phát hiện cut cảnh bằng histogram | ⚠️ Idle video không có cut cảnh |
| **Stillness detection** | Optical flow → frame motion thấp nhất | ✅ Chọn |

## Implementation: `avatar/stillness.py`

### Pre-compute (chạy 1 lần lúc khởi động)

```python
cap = cv2.VideoCapture(video_path)
prev_gray = None
motion_scores = []

while True:
    ret, frame = cap.read()
    if not ret: break
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    if prev_gray is not None:
        flow = cv2.calcOpticalFlowFarneback(prev_gray, gray, None,
                                            0.5, 3, 15, 3, 5, 1.2, 0)
        score = np.mean(np.sqrt(flow[..., 0]**2 + flow[..., 1]**2))
        motion_scores.append(score)
    prev_gray = gray

threshold = np.percentile(motion_scores, 20)  # bottom 20%
golden_frames = [i for i, s in enumerate(motion_scores) if s <= threshold]
```

### Runtime lookup

```python
# video_display.py
def _at_golden_frame(self) -> bool:
    current = int(self._idle_cap.get(cv2.CAP_PROP_POS_FRAMES))
    target = stillness.next_golden_frame(video_path, current, total_frames)
    if target is None:
        return True   # precompute chưa xong → switch ngay
    return abs(current - target) <= 1
```

Timeout fallback: **3 giây** — nếu không gặp golden frame trong 3s → switch ngay để không block.

## Kết quả

- Transition idle → lipsync: không giật (avatar ở tư thế neutral)
- Không delay quá lâu: tối đa 3s chờ thêm

## Files

| File | Vai trò |
|---|---|
| `avatar/stillness.py` | Golden frame computation + cache + lookup |
| `avatar/video_display.py` | `_at_golden_frame()`, `_GOLDEN_WAIT_TIMEOUT = 3.0` |
| `docs/.../04-lipsync-insertion-point-research.md` | Research đầy đủ 3 giải pháp MECE |
