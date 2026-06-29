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

---

## Phần 2 — Research Model Nhép Môi (Lipsync Model Selection)

**Cập nhật:** 2026-06-28
**Bối cảnh:** Wav2Lip CPU ~103s/clip 4.3s → không real-time được cho production livestream

### Hardware roadmap

| Giai đoạn | Hardware | Hướng giải pháp |
|-----------|---------|----------------|
| **Hiện tại** | CPU only | Cloud API hoặc chấp nhận delay lớn |
| **Sắp tới** | GPU NVIDIA (upgrade) | Local model real-time |

---

### Bài toán latency — MECE cases khi khách hỏi trên Livestream

Livestream thực tế: host (avatar Linh) đang nói chuyện liên tục. Khách comment → AI cần trả lời. Trong lúc chờ AI xử lý, host cần "fill" tự nhiên để không bị im lặng ngượng ngùng.

#### Case 1 — Khách hỏi về sản phẩm đang bán (Dr.Bee Nhộng Ong)

| Sub-case | Ví dụ | Độ dài reply | Latency chấp nhận |
|---------|-------|-------------|-----------------|
| 1a. Câu hỏi đơn giản | "giá bao nhiêu?", "mua ở đâu?" | 1-2 câu (~5s audio) | **< 5s** — phải nhanh, khách đang chờ giá |
| 1b. Câu hỏi chi tiết | "thành phần có gì?", "dùng cho tóc dầu được không?" | 3-4 câu (~12s audio) | **5-15s OK** — host có thể fill "Để Linh xem lại thông tin cho bạn nhé..." |
| 1c. Câu hỏi so sánh / objection | "sao đắt vậy?", "khác gì hàng khác?" | 4-5 câu (~18s audio) | **10-20s OK** — host fill "Câu hỏi hay lắm bạn ơi, để Linh giải thích nhé..." |

**→ Target latency cho Case 1: < 15s** (đủ để fill 1 câu bridge ngắn)

#### Case 2 — Khách hỏi sản phẩm khác / off-topic

| Sub-case | Ví dụ | Hành vi AI | Latency cần |
|---------|-------|-----------|------------|
| 2a. Sản phẩm cùng thương hiệu | "Dr.Bee có dầu gội không?" | Redirect khéo về Nhộng Ong | **< 5s** |
| 2b. Sản phẩm đối thủ | "X-Men ngon hơn không?" | Không so sánh, highlight Dr.Bee | **< 5s** |
| 2c. Hoàn toàn off-topic | "ai thắng World Cup?" | Nhẹ nhàng redirect về stream | **< 3s** — câu ngắn, không cần nghĩ nhiều |

**→ Target latency cho Case 2: < 5s** (reply ngắn, không cần elaborate)

#### Case 3 — Khách spam / troll / chửi

| Sub-case | Ví dụ | Hành vi AI | Latency cần |
|---------|-------|-----------|------------|
| 3a. Spam emoji / ký tự | "😂😂😂😂" | Bỏ qua hoặc reply vui | **< 2s** |
| 3b. Comment chửi / toxic | "đồ lừa đảo" | Calm down, không defend | **< 3s** — không được im lặng lâu |
| 3c. Hỏi "bạn có phải AI không?" | "mày là robot à?" | Khéo léo chuyển hướng | **< 5s** |

**→ Target latency cho Case 3: < 3s** (phản ứng nhanh = chuyên nghiệp)

#### Tổng kết latency target

```
Case 1 (sản phẩm đang bán):  < 15s  ← quan trọng nhất, chiếm ~70% comment
Case 2 (off-topic):           < 5s   ← chiếm ~20% comment
Case 3 (spam/troll):          < 3s   ← chiếm ~10% comment

→ Mục tiêu thiết kế hệ thống: P90 < 15s, P99 < 30s
```

**Fill content trong lúc chờ (quan trọng):**
- "Để Linh xem lại thông tin cho bạn nhé..." (~2s fill)
- "Câu hỏi hay quá bạn ơi..." (~1.5s fill)
- "Ừ bạn hỏi đúng lắm đó..." (~1.5s fill)
→ Tổng fill có thể che được 3-5s delay mà không bị lộ

---

### Landscape các model nhép môi hiện có

#### Nhóm A — Local Models (cần GPU để real-time)

| Model | Tổ chức | Tốc độ (RTX 3090) | Chất lượng | Ghi chú |
|-------|---------|-------------------|------------|---------|
| **Wav2Lip** *(đang dùng)* | Research | ~103s/4.3s clip (CPU) | ⭐⭐⭐ | Chuẩn baseline, chậm trên CPU |
| **MuseTalk** | Microsoft | Real-time ~30fps | ⭐⭐⭐⭐ | Thiết kế cho livestream, streaming avatar |
| **LatentSync** | ByteDance | Fast batch | ⭐⭐⭐⭐⭐ | Chất lượng cao nhất hiện tại |
| **LivePortrait** | Kuaishou | Very fast | ⭐⭐⭐⭐ | Portrait animation, không chỉ môi |
| **Video-Retalking** | Research | Medium | ⭐⭐⭐⭐ | Tốt hơn Wav2Lip, toàn khuôn mặt |
| **SadTalker** | Research | Slow | ⭐⭐⭐⭐ | Expressive, nhiều biểu cảm hơn |
| **Hallo / Hallo2** | Fudan | Medium | ⭐⭐⭐⭐ | Portrait + audio driven |
| **AniPortrait** | Research | Medium | ⭐⭐⭐ | Full portrait animation |
| **EchoMimic** | Ant Group | Fast | ⭐⭐⭐⭐ | Audio-driven, tự nhiên |
| **DiffTalk** | Research | Slow | ⭐⭐⭐ | Diffusion-based, chất lượng cao nhưng chậm |

#### Nhóm B — Cloud APIs (không cần GPU, trả tiền theo phút/request)

| Service | Latency | Giá | Chất lượng | Streaming? |
|---------|---------|-----|------------|-----------|
| **D-ID** | ~3-8s | ~$0.10/min | ⭐⭐⭐⭐ | Có streaming API |
| **HeyGen** | ~5-10s | ~$0.08/min | ⭐⭐⭐⭐⭐ | Có Streaming Avatar API |
| **Sync.so (Synclabs)** | ~2-5s | ~$0.05/min | ⭐⭐⭐⭐ | Chuyên lip sync, nhanh nhất |
| **Rask.ai** | ~5-15s | Theo plan | ⭐⭐⭐ | Thiên về dubbing hơn |
| **Hedra** | ~5-10s | Freemium | ⭐⭐⭐⭐ | Character video |
| **Tavus** | ~2-3s | Enterprise | ⭐⭐⭐⭐⭐ | Real-time conversational video |

---

### Đề xuất lộ trình chọn model

```
Giai đoạn HIỆN TẠI (CPU only):
  → Dùng Cloud API: Sync.so hoặc D-ID
  → Latency ~3-8s, đủ cho production với fill content
  → Chi phí: ~$10-50/tháng cho demo volume

Giai đoạn SẮP TỚI (có GPU):
  → Chuyển sang MuseTalk (real-time) hoặc LatentSync (quality cao nhất)
  → Latency < 1s, zero cost per request
  → Không phụ thuộc cloud
```

**→ Việc cần làm tiếp theo:** Test thử Sync.so API với 1 clip mẫu, so sánh chất lượng + latency với Wav2Lip hiện tại trước khi quyết định.
