# Hướng dẫn kết nối OBS — Demo AI Livestream Phase 1

## Mục tiêu
Quay màn hình web UI của Fay (http://127.0.0.1:5000) và audio giọng Linh để demo hoặc stream lên Facebook.

---

## Bước 1 — Cài OBS Studio

Tải tại: https://obsproject.com/download  
Cài đặt mặc định, không cần config đặc biệt.

---

## Bước 2 — Setup Scene trong OBS

### Tạo Scene mới
- Mở OBS → Scenes panel (góc dưới trái) → nhấn `+` → đặt tên `AI Livestream Demo`

### Thêm nguồn hình ảnh

**Option A — Capture toàn màn hình (đơn giản nhất)**
1. Sources → `+` → **Display Capture**
2. Chọn màn hình đang hiển thị browser
3. Crop bằng cách giữ `Alt` + kéo góc để chỉ lấy vùng avatar/chat

**Option B — Capture chỉ cửa sổ Browser (sạch hơn)**
1. Sources → `+` → **Window Capture**
2. Chọn `[chrome.exe]: Fay AI` hoặc tên cửa sổ browser
3. Đặt `Capture Method: Windows Graphics Capture`

### Thêm nguồn âm thanh (TTS output của Fay)
1. Sources → `+` → **Audio Output Capture**
2. Chọn `Default` hoặc thiết bị loa/headphone đang dùng
3. Fay phát audio qua speaker → OBS bắt lại tự động

---

## Bước 3 — Layout gợi ý cho Demo

```
┌─────────────────────────────────┐
│                                 │
│      Avatar / Web UI Fay        │
│      (http://127.0.0.1:5000)    │
│                                 │
│  ┌───────────────────────────┐  │
│  │  Chat / Comment Feed      │  │
│  │  DR.BEE 590K | Freeship  │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

Có thể thêm:
- Text overlay: tên sản phẩm + giá (Sources → `+` → **Text GDI+**)
- Logo Dr.Bee góc trên (Sources → `+` → **Image**)
- Banner "LIVE" nhấp nháy (Sources → `+` → **Media Source** → file gif)

---

## Bước 4 — Test âm thanh

1. Trong Fay UI, gõ comment vào ô chat → nhấn Send
2. Linh sẽ trả lời bằng giọng Hoài My tiếng Việt
3. Kiểm tra Audio Mixer trong OBS — thanh xanh phải nhảy khi Linh nói
4. Nếu không có âm thanh: vào OBS Settings → Audio → chọn đúng thiết bị output

---

## Bước 5 — Ghi video demo (không cần Facebook)

**Chỉ cần ghi màn hình:**
1. OBS → Start Recording (góc dưới phải)
2. Nhập các comment mẫu vào Fay:
   - "dầu gội nhộng ong là gì"
   - "giá bao nhiêu"
   - "còn hàng không"
   - "mua sao"
3. Stop Recording → video lưu tại `C:\Users\[tên]\Videos`

---

## Bước 6 — Stream lên Facebook (Phase 2)

> Chỉ thực hiện sau khi Phase 1 demo pass.

1. Vào Facebook → Trang Dr.Bee → **Live Video** → **Sử dụng phần mềm stream**
2. Copy **Stream Key** từ Facebook
3. OBS → Settings → Stream:
   - Service: `Facebook Live`  
   - Stream Key: dán vào
4. OBS → **Start Streaming**

**Lưu ý Phase 2:**
- Upload speed tối thiểu 5 Mbps để stream 720p ổn định
- Chạy Fay + OBS cùng lúc cần RAM ≥ 8GB
- Tắt các ứng dụng nặng khác khi stream

---

## Troubleshooting

| Vấn đề | Giải pháp |
|--------|-----------|
| OBS không bắt được âm thanh | Kiểm tra Audio Output Capture → chọn đúng thiết bị |
| Màn hình đen trong OBS | Đổi Display Capture sang Window Capture |
| Giọng Linh bị lag | Giảm bitrate audio trong Fay settings |
| Facebook từ chối stream | Kiểm tra stream key còn hạn, tốc độ upload |
