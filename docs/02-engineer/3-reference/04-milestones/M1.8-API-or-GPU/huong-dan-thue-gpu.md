# Hướng Dẫn Chọn & Thuê GPU cho AI Livestream

> Tài liệu này hướng dẫn chọn GPU phù hợp để chạy **VieNeu-TTS + MuseTalk** cho hệ thống AI Livestream trên nền tảng cho thuê GPU.

---

## 1. Yêu cầu VRAM tối thiểu

| Model | VRAM cần |
|-------|---------|
| VieNeu-TTS v3 Turbo | ~3-4GB |
| VieNeu-TTS v2 (full quality) | ~6GB |
| MuseTalk | ~6-8GB |
| **Tổng (v3 Turbo + MuseTalk)** | **~10-12GB** |
| **Tổng (v2 + MuseTalk)** | **~12-14GB** |

---

## 2. So sánh GPU phù hợp

| GPU | VRAM | Phù hợp | Ghi chú |
|-----|------|---------|---------|
| RTX 3060 12GB | 12GB | ⚠️ Vừa đủ | Chỉ chạy được v3 Turbo + MuseTalk, không có headroom |
| RTX 3070 8GB | 8GB | ❌ Thiếu | Không đủ chạy song song |
| RTX 3080 10GB | 10GB | ❌ Thiếu | Không đủ chạy v2 + MuseTalk |
| RTX 3080 Ti 16GB | 16GB | ✅ Được | Đủ cho v3 Turbo + MuseTalk |
| **RTX 3090 24GB** | **24GB** | ✅ **Khuyến nghị** | Thoải mái, dư dả, chạy được v2 + MuseTalk |
| RTX 4070 Ti 12GB | 12GB | ⚠️ Vừa đủ | Nhanh hơn 3060, nhưng vẫn sát VRAM |
| RTX 4080 16GB | 16GB | ✅ Tốt | Đủ cho v2 + MuseTalk |
| RTX 4090 24GB | 24GB | ✅ Ngon nhất | Đắt hơn 3090 không cần thiết |

### ✅ Lựa chọn tối ưu: RTX 3090 24GB

```
VRAM phân bổ khi chạy:
24GB tổng
├── MuseTalk          ~6-8GB
├── VieNeu-TTS v2     ~6GB
├── Buffer/overhead   ~2GB
└── Còn dư            ~8-10GB ✅ An toàn
```

---

## 3. Lưu ý quan trọng khi thuê

### Uptime
- **99%+** → Máy ổn định, phù hợp cho production
- **93-98%** → Chấp nhận được cho test
- **< 93%** → Tránh dùng cho livestream thật

### Thời gian thuê tối đa
- Nhiều provider giới hạn **120 giờ (~5 ngày)**
- Dữ liệu có thể **bị xóa** khi hết hạn
- **Giải pháp:** Lưu model weights ra ngoài trước khi hết hạn, hoặc dùng volume/storage gắn ngoài

### RAM hệ thống
- Tối thiểu **16GB RAM** để chạy 2 model song song
- **28GB+** là lý tưởng

---

## 4. Chọn Template khi khởi động

| Template | Khuyến nghị | Lý do |
|----------|------------|-------|
| **CUDA 12.9 Ubuntu 24.04** | ✅ **Chọn cái này** | Mới nhất, tương thích tốt nhất với PyTorch 2.x, VieNeu-TTS, MuseTalk |
| CUDA 12.4 Ubuntu 22.04 | ⚠️ Được | Hơi cũ nhưng vẫn dùng được |
| CUDA 12.0 Ubuntu 20.04 | ❌ Không nên | Quá cũ |
| PyTorch | ⚠️ Được | Có sẵn PyTorch nhưng không rõ version |
| Ubuntu 22.04 (bare) | ❌ Không | Không có CUDA sẵn |
| ComfyUI / A1111 | ❌ Không | Dành cho image generation |
| VSCode + Jupyter | ❌ Không cần | Nặng, không cần thiết |

---

## 5. Setup sau khi thuê GPU

### Bước 1: Kiểm tra GPU

```bash
nvidia-smi
# Kỳ vọng thấy: RTX 3090, 24GB, CUDA 12.x
```

### Bước 2: Cài PyTorch

```bash
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
python -c "import torch; print(torch.cuda.is_available())"
# Kỳ vọng: True
```

### Bước 3: Cài VieNeu-TTS

```bash
# Cài bản GPU (đầy đủ tính năng)
pip install "vieneu[gpu]"

# Kiểm tra
python -c "from vieneu import Vieneu; tts = Vieneu(); print('VieNeu OK')"
```

### Bước 4: Cài MuseTalk

```bash
git clone https://github.com/TMElyralab/MuseTalk.git
cd MuseTalk
pip install -r requirements.txt

# Tải model weights
python scripts/download_models.py
```

### Bước 5: Chạy VieNeu-TTS server

```bash
# Chạy API server tại port 7860
uv run vieneu-web
# hoặc
python -m vieneu.server --port 7860
```

### Bước 6: Chạy MuseTalk server

```bash
cd MuseTalk
python -m scripts.inference_server --port 8080
```

---

## 6. Tích hợp vào Fay

Sau khi 2 server chạy trên GPU cloud, cấu hình Fay tại `system.conf`:

```ini
# TTS: trỏ về VieNeu-TTS server trên GPU cloud
tts_module=vieneu
vieneu_api_url=http://<IP_GPU_SERVER>:7860

# Lip sync: trỏ về MuseTalk server
musetalk_api_url=http://<IP_GPU_SERVER>:8080
```

---

## 7. Chi phí ước tính

### RTX 3090 24GB — Stream 8h/ngày

| Thời gian | Chi phí |
|-----------|---------|
| 1 ngày | ~33,600đ (~$1.35) |
| 1 tuần | ~235,000đ (~$9.4) |
| 1 tháng | ~1,008,000đ (~$40) |

> Giá tham khảo: ~4,200đ/giờ (có thể thay đổi theo provider)

### So sánh với API cloud

| Giải pháp | Chi phí/tháng (stream 8h/ngày) |
|-----------|-------------------------------|
| ElevenLabs Pro + Sync.so | ~$150-200 (~3,750,000đ) |
| **Self-host RTX 3090** | **~$40 (~1,008,000đ)** |
| **Tiết kiệm** | **~75%** |

---

## 8. Checklist trước khi thuê

- [ ] Kiểm tra uptime của máy (> 95% cho production)
- [ ] Xem thời gian thuê tối đa (có đủ cho kế hoạch không)
- [ ] Chọn template **CUDA 12.9 Ubuntu 24.04**
- [ ] Đảm bảo RAM hệ thống ≥ 16GB
- [ ] Chuẩn bị script backup model weights tự động
- [ ] Chuẩn bị script auto-restart service khi máy reboot

---

## 9. Script Auto-restart (Khuyến nghị)

Tạo file `/etc/systemd/system/vieneu.service`:

```ini
[Unit]
Description=VieNeu TTS Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/workspace/VieNeu-TTS
ExecStart=/usr/bin/python -m vieneu.server --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable vieneu
sudo systemctl start vieneu
```

---

*Tài liệu được tạo: 2026-07-01*
*Cập nhật: Khi có thay đổi về model hoặc pricing*
