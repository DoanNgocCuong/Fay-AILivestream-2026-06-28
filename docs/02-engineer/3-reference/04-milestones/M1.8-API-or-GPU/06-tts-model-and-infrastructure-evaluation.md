# Đánh Giá Model Text-to-Speech & Giải Pháp Infrastructure

> Mục tiêu: Chọn model TTS và phương thức triển khai tối ưu cho pipeline livestream **10h/ngày**, ưu tiên tiếng Việt tự nhiên và latency thấp.

---

## 1. Đánh Giá Model TTS

### 1.1 Tổng quan các model

| Model                      | Tiếng Việt | Chất lượng | Latency | License       | Loại |
| -------------------------- | ------------ | ------------- | ------- | ------------- | ----- |
| **F5-TTS**           | ⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐    | ~200ms  | MIT           | Local |
| **CosyVoice 2**      | ⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐    | ~300ms  | Apache 2.0    | Local |
| **MeloTTS**          | ⭐⭐⭐       | ⭐⭐⭐⭐      | ~100ms  | MIT           | Local |
| **StyleTTS2**        | ⭐⭐⭐       | ⭐⭐⭐⭐⭐    | ~300ms  | MIT           | Local |
| **Coqui XTTS v2**    | ⭐⭐⭐⭐     | ⭐⭐⭐⭐      | ~400ms  | CPML          | Local |
| **ElevenLabs**       | ⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐    | ~500ms  | Thương mại | API   |
| **OpenAI TTS**       | ⭐⭐⭐       | ⭐⭐⭐⭐      | ~400ms  | Thương mại | API   |
| **FPT.AI TTS**       | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐      | ~300ms  | Thương mại | API   |
| **Zalo TTS**         | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐      | ~200ms  | Thương mại | API   |
| **Google Cloud TTS** | ⭐⭐⭐⭐     | ⭐⭐⭐⭐      | ~300ms  | Thương mại | API   |

---

### 1.2 Chi tiết từng model

#### F5-TTS ✅ Khuyến nghị (Local)

- Zero-shot voice cloning — clone giọng từ 10-30 giây audio mẫu
- Tiếng Việt tự nhiên, ít lỗi dấu thanh
- Latency ~200ms trên RTX 3090 (đủ real-time)
- Không tốn phí API, chạy hoàn toàn local
- Tích hợp Python đơn giản
- **Phù hợp nhất cho pipeline Fay**

#### CosyVoice 2

- Của Alibaba, chất lượng rất cao
- Hỗ trợ đa ngôn ngữ kể cả tiếng Việt
- Streaming mode có sẵn (quan trọng cho real-time)
- VRAM cần ~6GB
- Cộng đồng đang tăng trưởng nhanh

#### MeloTTS

- Nhẹ nhất trong các model local (~2GB VRAM)
- Latency thấp nhất (~100ms)
- Chất lượng thấp hơn F5-TTS một chút
- Phù hợp khi VRAM hạn chế

#### ElevenLabs (API)

- Chất lượng giọng tốt nhất thị trường
- Voice cloning cực kỳ tự nhiên
- Tiếng Việt ngày càng cải thiện
- **Chi phí cao** cho 10h/ngày

#### FPT.AI TTS (API)

- Tiếng Việt tốt nhất trong các API thương mại Việt Nam
- Nhiều giọng đọc (Nam/Nữ, miền Bắc/Nam)
- Giá rẻ hơn ElevenLabs
- Latency ổn định ~200-300ms

#### Zalo TTS (API)

- Tiếng Việt chuẩn, tự nhiên
- Free tier có sẵn
- Phù hợp test nhanh

---

### 1.3 Yêu cầu phần cứng (Local models)

| Model         | CPU             | GPU      | RAM  | VRAM  |
| ------------- | --------------- | -------- | ---- | ----- |
| F5-TTS        | ✅ Chậm        | ✅ Nhanh | 8GB  | 4-6GB |
| CosyVoice 2   | ⚠️ Rất chậm | ✅       | 16GB | 6-8GB |
| MeloTTS       | ✅ Được      | ✅       | 4GB  | 2GB   |
| StyleTTS2     | ⚠️ Chậm      | ✅       | 8GB  | 4GB   |
| Coqui XTTS v2 | ⚠️ Chậm      | ✅       | 8GB  | 4-6GB |

---

## 2. Đánh Giá Phương Thức Triển Khai

### 2.1 Giả định tính toán

- Livestream: **10 giờ/ngày**, 30 ngày/tháng
- TTS hoạt động ~60% thời gian (avatar đang nói): ~180 giờ/tháng
- Trung bình ~150 ký tự/giây khi nói

---

### 2.2 Option A — Dùng API

**Chi phí các nhà cung cấp:**

| Provider         | Giá             | Free tier           | Tiếng Việt |
| ---------------- | ---------------- | ------------------- | ------------ |
| ElevenLabs       | $0.30/1k ký tự | 10k ký tự/tháng  | ⭐⭐⭐⭐     |
| OpenAI TTS       | $15/1M ký tự   | Không              | ⭐⭐⭐       |
| Google Cloud TTS | $4/1M ký tự    | 1M ký tự/tháng   | ⭐⭐⭐⭐     |
| FPT.AI           | $2/1M ký tự    | 1M ký tự/tháng   | ⭐⭐⭐⭐⭐   |
| Zalo TTS         | ~$1/1M ký tự   | Có                 | ⭐⭐⭐⭐⭐   |
| Azure TTS        | $4/1M ký tự    | 0.5M ký tự/tháng | ⭐⭐⭐⭐     |

**Ước tính ký tự/tháng:**

```
150 ký tự/giây × 3600s × 180h = ~97,200,000 ký tự/tháng (~97M ký tự)
```

**Chi phí ước tính/tháng:**

```
ElevenLabs : 97M × $0.30/1k  = ~$29,100/tháng  ❌
OpenAI TTS : 97M × $15/1M    = ~$1,455/tháng   ❌
Google TTS : 97M × $4/1M     = ~$388/tháng     ⚠️
FPT.AI     : 97M × $2/1M     = ~$194/tháng     ⚠️
Zalo TTS   : 97M × $1/1M     = ~$97/tháng      ✅ (chấp nhận được)
```

**Đánh giá:**

- ✅ Không cần GPU riêng cho TTS (chia sẻ GPU với lip sync)
- ✅ Zalo TTS / FPT.AI chi phí hợp lý và tiếng Việt tốt
- ⚠️ Phụ thuộc kết nối internet
- ⚠️ Latency network cộng thêm 100-300ms
- ❌ ElevenLabs quá đắt cho volume này

**Kết luận**: ✅ **Zalo TTS hoặc FPT.AI phù hợp nếu không muốn dùng GPU cho TTS**

---

### 2.3 Option B — Local Model (Chạy chung GPU với Lip Sync)

**Kịch bản chia sẻ GPU (RTX 3090 - 24GB VRAM):**

```
MuseTalk (Lip Sync) : ~8GB VRAM
F5-TTS (TTS)        : ~5GB VRAM
Buffer              : ~11GB còn lại
Tổng                : ~13GB / 24GB → ✅ Đủ dùng
```

**Chi phí thêm:**

```
$0/tháng — chạy chung GPU đã có cho lip sync
Chỉ tốn thêm RAM và xử lý song song
```

**Đánh giá:**

- ✅ Chi phí = $0 (tận dụng GPU đã có)
- ✅ Latency thấp nhất (~100-200ms local)
- ✅ Không phụ thuộc internet
- ✅ Privacy tốt (không gửi text ra ngoài)
- ⚠️ Cần quản lý VRAM cẩn thận
- ⚠️ Setup phức tạp hơn

**Kết luận**: ✅ **Tối ưu nhất — chạy F5-TTS local trên cùng GPU với MuseTalk**

---

### 2.4 Option C — Hybrid (API + Local)

**Chiến lược:**

- Dùng **API (Zalo/FPT.AI)** trong giai đoạn test và thuê GPU
- Chuyển sang **Local F5-TTS** khi mua GPU

```
Giai đoạn test    → Zalo TTS API (free tier đủ dùng)
Giai đoạn thuê GPU → FPT.AI API (~$97/tháng) hoặc Local trên GPU thuê
Giai đoạn mua GPU → F5-TTS local ($0/tháng)
```

---

## 3. So Sánh Tổng Hợp

| Tiêu chí           | API (ElevenLabs)          | API (Zalo/FPT) | Local (F5-TTS)   |
| -------------------- | ------------------------- | -------------- | ---------------- |
| Chi phí/tháng      | ~$29,000 ❌ | ~$97-194 ✅ | $0 ✅✅        |                  |
| Tiếng Việt         | ⭐⭐⭐⭐                  | ⭐⭐⭐⭐⭐     | ⭐⭐⭐⭐         |
| Chất lượng giọng | ⭐⭐⭐⭐⭐                | ⭐⭐⭐⭐       | ⭐⭐⭐⭐⭐       |
| Latency              | ~400-500ms                | ~200-300ms     | ~100-200ms       |
| Real-time            | ⚠️                      | ✅             | ✅               |
| Setup                | ✅ Dễ                    | ✅ Dễ         | ⚠️ Trung bình |
| Privacy              | ❌                        | ❌             | ✅               |
| Phụ thuộc internet | ❌ Có                    | ❌ Có         | ✅ Không        |

---

## 4. Kết Hợp Với Pipeline Fay

### VRAM budget trên RTX 3090 (24GB):

```
┌─────────────────────────────────────┐
│ MuseTalk (Lip Sync)    ~8GB         │
│ F5-TTS (TTS)           ~5GB         │
│ LLM nhỏ (tùy chọn)    ~4GB         │
│ Buffer / OS            ~3GB         │
│ Còn trống              ~4GB         │
└─────────────────────────────────────┘
Tổng sử dụng: ~20GB / 24GB → ✅ An toàn
```

### Pipeline end-to-end latency mục tiêu:

```
User nói  →  STT      →  LLM       →  TTS (F5)  →  Lip Sync   →  Stream
          ~300ms        ~500ms       ~200ms        ~150ms         ~50ms
                                                        
Tổng latency: ~1.2 giây → Chấp nhận được cho livestream
```

---

## 5. Lộ Trình Khuyến Nghị

```
Phase 1 — Test miễn phí (Tuần 1-2)
├── Zalo TTS API (free tier)
├── Test chất lượng tiếng Việt
└── Validate tích hợp với Fay pipeline

Phase 2 — Thuê GPU (Tháng 1-2)
├── Chạy F5-TTS local trên GPU thuê
├── So sánh latency local vs API
├── Fine-tune giọng với voice cloning
└── Chi phí: $0 thêm (dùng chung GPU với MuseTalk)

Phase 3 — Mua GPU (Tháng 3+)
├── F5-TTS local trên RTX 3090 riêng
├── Chi phí TTS: $0/tháng
└── Toàn bộ pipeline chạy local, không phụ thuộc internet
```

---

## 6. Nguồn Tham Khảo

- [F5-TTS GitHub](https://github.com/SWivid/F5-TTS)
- [CosyVoice 2 GitHub](https://github.com/FunAudioLLM/CosyVoice)
- [MeloTTS GitHub](https://github.com/myshell-ai/MeloTTS)
- [Coqui XTTS v2](https://github.com/coqui-ai/TTS)
- [FPT.AI TTS](https://fpt.ai/tts)
- [Zalo TTS](https://zalo.ai/docs/api/tts)
- [ElevenLabs](https://elevenlabs.io)

