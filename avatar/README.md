# Avatar Lip Sync Module

Tính năng phát video liên tục + nhép môi realtime cho AI Livestream.

## Kiến trúc

```
[Fay TTS] → audio.wav
     ↓ (async, không block)
[lip_sync.py] → Wav2Lip inference
     ↓
[video_display.py] → OpenCV window
     ↓
[OBS Window Capture] → Livestream
```

## Cài đặt

```bat
cd avatar
setup.bat
```

Script tự động:
1. Cài `opencv-python`, `numpy`
2. Clone Wav2Lip từ GitHub
3. Cài requirements Wav2Lip
4. Tải checkpoint `wav2lip_gan.pth`

## Chuẩn bị avatar

Đặt video avatar vào:
```
avatar/assets/avatar_idle.mp4   ← video vòng lặp khi im lặng
avatar/assets/avatar.jpg        ← ảnh tĩnh (fallback nếu không có video)
```

Video `Facebook.mp4` đã được copy vào `avatar/assets/avatar_idle.mp4`.

**Yêu cầu video:**
- Khuôn mặt rõ, nhìn thẳng
- Ánh sáng đều
- Càng ít chuyển động đầu càng tốt (Wav2Lip hoạt động tốt hơn)

## Kết nối OBS

1. Mở Fay → AI tự mở cửa sổ **"Linh - Dr.Bee AI Host"**
2. Trong OBS: **Add Source → Window Capture → chọn cửa sổ đó**
3. Scale to fit scene
4. Start Streaming

## Pipeline hoạt động như thế nào

| Trạng thái | Màn hình hiển thị |
|-----------|------------------|
| Chờ comment | Video `avatar_idle.mp4` lặp vô tận |
| Khách comment → AI trả lời | TTS tạo audio → Wav2Lip xử lý (~2-3s) |
| Lip sync xong | Phát video nhép môi |
| Video nhép môi xong | Quay lại idle loop |

## Delay thực tế trên CPU

| CPU | Thời gian xử lý / câu |
|-----|----------------------|
| Intel i5 | ~8-15s |
| Intel i7 | ~4-8s |
| AMD Ryzen 7 | ~3-6s |

> Với GPU (NVIDIA): ~0.5-1s — nếu có GPU, cài CUDA và Wav2Lip tự dùng.

## Cấu hình nâng cao

Chỉnh trong `avatar/config.py`:
- `WIDTH`, `HEIGHT`: kích thước cửa sổ (mặc định 720x1280 portrait)
- `FPS`: frame rate (mặc định 25)
- `AVATAR_VIDEO_PATH`: đường dẫn video khác
