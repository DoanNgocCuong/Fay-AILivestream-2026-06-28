# Nghiên cứu: Smart Insertion Point cho Lip Sync

**Ngày:** 2026-06-28
**Trạng thái:** Research done — chưa implement

---

## Bài toán

Hiện tại khi Wav2Lip xử lý xong, video idle đang phát bị dừng đột ngột tại một frame **ngẫu nhiên** để chèn video nhép môi vào. Trông rất giật.

**Mục tiêu:** Tìm điểm dừng "tự nhiên" trong video đang phát — ví dụ lúc nhân vật đứng yên, hoặc trùng khoảng lặng trong audio — rồi mới chèn lip sync vào.

---

## Brainstorm MECE các giải pháp

### Nhóm A — Phân tích Video (offline, trước khi play)

| # | Giải pháp | Mô tả |
|---|-----------|-------|
| A1 | **Pre-compute stillness frames** | Khi load video, dùng optical flow tính motion score từng frame. Lưu danh sách frame có chuyển động thấp nhất → "điểm dừng đẹp" |
| A2 | **Silence-aligned frames** | Tìm các frame trùng với khoảng lặng trong audio track của video. Người nói thường dừng hít thở → frame lúc đó tự nhiên nhất |
| A3 | **Shot boundary detection** | Phát hiện điểm chuyển cảnh, dừng ngay trước/sau transition |
| A4 | **Facial landmark neutral pose** | Dùng MediaPipe/dlib tìm frame khuôn mặt ở vị trí trung lập nhất (mắt nhìn thẳng, miệng khép) |

### Nhóm B — Phân tích Realtime (trong khi video đang play)

| # | Giải pháp | Mô tả |
|---|-----------|-------|
| B1 | **Look-ahead buffer scoring** | Khi Wav2Lip bắt đầu xử lý, đồng thời buffer 2-3s frame sắp tới và score chúng. Khi lipsync ready → pause tại frame score cao nhất trong buffer |
| B2 | **Frame diff threshold** | Realtime so sánh diff giữa frame hiện tại và frame kế tiếp. Khi diff < threshold → moment tĩnh, pause được |
| B3 | **Audio energy detect** | Monitor energy của audio video đang play. Khi energy drop (khoảng lặng) → pause ngay đó |

### Nhóm C — Heuristic / Logic đơn giản

| # | Giải pháp | Mô tả |
|---|-----------|-------|
| C1 | **Loop boundary only** | Chỉ pause tại frame 0 (đầu loop). Đợi video đang play kết thúc 1 vòng rồi mới insert lipsync |
| C2 | **Minimum play duration** | Phải play tối thiểu X giây trước khi cho phép pause. Tránh pause quá sớm gây giật |
| C3 | **Fixed interval checkpoints** | Chia video thành checkpoint cố định (mỗi 2s). Lipsync ready → đợi checkpoint kế tiếp rồi pause |

### Nhóm D — AI/LLM quyết định

| # | Giải pháp | Mô tả |
|---|-----------|-------|
| D1 | **LLM phân tích video transcript** | Nếu video có transcript, cho LLM chọn "điểm nghỉ ngữ nghĩa" hợp lý để chèn |
| D2 | **Vision model caption frames** | Dùng Gemini Vision xem từng frame, hỏi "frame này có phù hợp để pause không?" |
| D3 | **AI dự đoán thời điểm** | AI tính: Wav2Lip cần ~Xs → đặt lịch pause vào giây X+buffer trong tương lai |

---

## Đánh giá

| Giải pháp | Chất lượng tự nhiên | Độ phức tạp | Latency thêm | Dependency |
|-----------|---------------------|-------------|--------------|------------|
| A1 Pre-compute stillness | ⭐⭐⭐⭐ | Thấp | 0ms | OpenCV (đã có) |
| A2 Silence-aligned | ⭐⭐⭐⭐⭐ | Thấp | 0ms | pygame (đã có) |
| B1 Look-ahead buffer | ⭐⭐⭐⭐ | Trung bình | <500ms | OpenCV (đã có) |
| B2 Frame diff realtime | ⭐⭐⭐ | Thấp | <100ms | OpenCV (đã có) |
| C1 Loop boundary | ⭐⭐ | Rất thấp | 0–video_duration | Không có |
| D2 Vision model | ⭐⭐⭐⭐⭐ | Rất cao | 2-5s | Gemini API |
| D3 AI dự đoán thời điểm | ⭐⭐⭐ | Trung bình | 0ms | Gemini API |

---

## 3 Giải pháp được chọn

### 🥇 Giải pháp 1 — Pre-compute Stillness + Silence Frames (A1 + A2)

**Ý tưởng:** Xử lý video 1 lần lúc khởi động, lưu sẵn danh sách "điểm vàng".

**Flow:**
```
Lúc khởi động (1 lần duy nhất):
  → Đọc toàn bộ video
  → Optical flow: tính motion score từng frame
  → Audio track: tìm silence gaps
  → Merge: frame tĩnh + trùng audio lặng = "điểm vàng"
  → Lưu: good_frames = [12, 47, 89, 134, ...]

Khi lipsync ready:
  → current_frame = cap.get(CAP_PROP_POS_FRAMES)
  → next_good = min(f for f in good_frames if f >= current_frame)
  → Advance video đến next_good → pause → play lipsync
```

**Ưu điểm:** Zero latency khi pause, chất lượng cao, chỉ dùng OpenCV + pygame đã có
**Nhược điểm:** Tốn ~2-5s lúc startup để pre-process video (chạy 1 lần)

---

### 🥈 Giải pháp 2 — Look-ahead Buffer Scoring (B1)

**Ý tưởng:** Khi Wav2Lip bắt đầu chạy, song song score các frame sắp tới.

**Flow:**
```
Khi Wav2Lip bắt đầu (t=0):
  → Spawn thread: buffer 3s frame tiếp theo
  → Score từng frame: score = 1 / (motion_score + epsilon)

Khi Wav2Lip xong (t≈10s):
  → Query: frame tốt nhất trong 0.5s tới?
  → Đợi tối đa 500ms cho đến frame đó
  → Pause → play lipsync
```

**Ưu điểm:** Không tốn startup time, adaptive theo nội dung đang play
**Nhược điểm:** Thêm <500ms delay so với Giải pháp 1

---

### 🥉 Giải pháp 3 — AI Timing Predictor (D3)

**Ý tưởng:** Dự đoán trước khi nào Wav2Lip xong, schedule pause từ sớm.

**Flow:**
```
Khi TTS tạo xong audio:
  → audio_duration = get_audio_length(audio_path)  # seconds
  → estimate = audio_duration * CPU_FACTOR + OVERHEAD  # calibrate theo máy
  → target_pause_time = now + estimate
  → Schedule: tại target_pause_time, tìm frame tốt nhất ±1s
  → Pause → lipsync vừa xong đúng lúc
```

**Ưu điểm:** Prepare trước, ít giật nhất khi kết hợp với Giải pháp 1 hoặc 2
**Nhược điểm:** Cần calibrate CPU_FACTOR theo từng máy; lần đầu có thể lệch

---

## Thứ tự triển khai đề xuất

```
Bước 1: Giải pháp 1 (pre-compute)
  → Dễ nhất, không cần dependency mới
  → Implement trong VideoDisplay._run() lúc startup

Bước 2: Giải pháp 3 (timing predictor) — ghép vào pipeline.py
  → Dùng để tune timing, giảm gap giữa lipsync ready và pause thực tế

Bước 3: Giải pháp 2 (look-ahead) — nếu video dài, startup quá chậm
  → Thay thế Giải pháp 1 nếu cần
```

---

## File cần sửa khi implement

| File | Thay đổi |
|------|---------|
| `avatar/video_display.py` | Thêm `_precompute_good_frames()` trong `_run()`, sửa logic pause |
| `avatar/pipeline.py` | Thêm timing predictor, notify display trước khi lipsync xong |
| `avatar/config.py` | Thêm `MOTION_THRESHOLD`, `SILENCE_THRESHOLD`, `CPU_FACTOR` |
