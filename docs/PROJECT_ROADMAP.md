# Roadmap: Fay AI Livestream — Dr.Bee Sales Host

**Mục tiêu cuối cùng:** Chạy 24/7 một AI Avatar tên **Linh** tự động trả lời comment trực tiếp trên Facebook Livestream, có khả năng nói và nhép môi realtime, quản lý được qua web UI.

**Repo:** https://github.com/DoanNgocCuong/Fay-AILivestream-2026-06-28

---

## Tổng quan các Phase

```
Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5
AI Sales     Avatar       Lip Sync    Facebook    Quản lý
Host cơ bản  Video Loop   Wav2Lip     Live        & Monitor
✅ DONE      ✅ DONE      ✅ code     ⬜ TODO     ⬜ TODO
                          ⏳ test
```

---

## Phase 1 — AI Sales Host cơ bản ✅ HOÀN THÀNH

**Mục đích:** Xây nền tảng — AI biết mình là ai, bán gì, nói tiếng Việt.

### Kết quả đạt được

| Hạng mục | Chi tiết |
|---------|---------|
| **Persona** | Linh — AI Sales Host thương hiệu Dr.Bee |
| **Sản phẩm** | Nhộng Ong Dưỡng Tóc Dr.Bee (combo 590K) |
| **Giọng nói** | Edge-TTS tiếng Việt: Hoài My (nữ) + Nam Minh (nam) |
| **AI Model** | Google Gemini 2.5 Flash (OpenAI-compatible endpoint) |
| **Knowledge base** | 16 cặp Q&A sản phẩm Dr.Bee (qa.csv) |
| **UI** | Dịch toàn bộ từ tiếng Trung → tiếng Việt (5 files) |
| **Bảo mật** | API key không commit, system.conf trong .gitignore |

### Luồng hoạt động
```
Người dùng gõ/comment
      ↓
Fay AI (Gemini 2.5 Flash)
      ↓
Text reply → Edge-TTS → audio .wav
      ↓
Phát ra loa / gửi về browser
```

---

## Phase 2 — Avatar Video Display ✅ HOÀN THÀNH

**Mục đích:** Tạo cửa sổ video avatar để OBS capture, phát liên tục có tiếng.

### Kết quả đạt được

| Hạng mục | Chi tiết |
|---------|---------|
| **Video idle** | Loop `avatar_idle.mp4` (Facebook.mp4) liên tục |
| **Audio** | Tách audio từ mp4 → wav (imageio-ffmpeg), phát bằng pygame |
| **A/V sync** | Audio-clock driven sync — dùng pygame position làm master clock, video đuổi theo |
| **Auto-fit** | Tự đọc FPS + kích thước từ video, scale vừa màn hình (letterbox) |
| **OBS** | Capture cửa sổ "Linh - Dr.Bee AI Host" → nguồn video cho stream |

### Luồng hoạt động
```
Fay start → VideoDisplay daemon thread
      ↓
OpenCV window "Linh - Dr.Bee AI Host" mở
      ↓
┌─────────────────────────────────────┐
│  IDLE MODE (mặc định)               │
│  - cv2: decode frames từ mp4        │
│  - pygame: phát audio song song     │
│  - khi video hết: loop lại từ đầu  │
└─────────────────────────────────────┘
      ↓ (khi AI reply xong lip sync)
┌─────────────────────────────────────┐
│  SPEAKING MODE                      │
│  - phát video nhép môi 1 lần        │
│  - kèm audio giọng AI               │
│  → tự về IDLE khi xong             │
└─────────────────────────────────────┘
```

---

## Phase 3 — Lip Sync Wav2Lip ✅ Code done / ⏳ Chờ test thực tế

**Mục đích:** Khi AI trả lời, avatar nhép môi khớp với tiếng — trông như người thật đang nói.

### Kết quả đạt được (code)

| Hạng mục | Chi tiết |
|---------|---------|
| **Engine** | Wav2Lip (Rudrabha/Wav2Lip trên GitHub) |
| **Input** | audio.wav (Edge-TTS output) + avatar_idle.mp4 (khuôn mặt) |
| **Output** | lipsync_xxx.mp4 (video nhép môi, ~3-15s xử lý tùy CPU) |
| **Async** | Worker thread riêng, không block TTS pipeline |
| **Timing** | Audio TTS bị hold lại đến khi video lip sync ready → phát đồng bộ |

### Luồng hoạt động
```
Fay AI reply → text
      ↓
Edge-TTS → audio.wav (giọng Linh)
      ↓
avatar/pipeline.py: on_audio_ready(audio.wav)
      ↓
lip_sync.py: worker thread (async)
      ↓
Wav2Lip subprocess (~3-15s)
[avatar_idle.mp4 + audio.wav] → lipsync_xxx.mp4
      ↓
VideoDisplay.play_lipsync(lipsync_xxx.mp4)
      ↓
Mode SPEAKING: phát video nhép môi + audio
      ↓
Xong → về IDLE loop
```

### Việc cần làm để hoàn thành Phase 3
```bash
# Bước 1: Cài Wav2Lip (chỉ làm 1 lần, ~1.5GB)
cd D:\GIT\Fay\avatar
setup.bat

# Bước 2: Chạy Fay và test
cd D:\GIT\Fay
set PYTHONUTF8=1
python main.py start

# Bước 3: Gõ tin nhắn test trong web UI → xem avatar có nhép môi không
```

---

## Phase 4 — Kết nối Facebook Live ⬜ TODO

**Mục đích:** Fay tự lắng nghe comment Facebook Live và tự trả lời — không cần người điều phối.

### Kiến trúc cần xây

```
Facebook Live Stream
      │
      │ (người xem comment)
      ▼
Facebook Graph API / Comment webhook
      │
      ▼
Comment Listener Service (Python)
  - Subscribe page webhook
  - Filter comments từ livestream
  - Loại bỏ spam, bot
      │
      ▼
Fay AI (input comment text)
      │
      ▼
AI reply → TTS → Lip Sync → Video
      │
      ▼
Hiển thị reply dưới dạng comment reply trên FB
      +
      ▼
OBS stream video avatar lên Facebook Live
```

### Các task cần làm

| # | Task | Độ khó |
|---|------|-------|
| 4.1 | Tạo Facebook App, cấu hình Webhook nhận comment | Trung bình |
| 4.2 | Viết comment listener service (nghe realtime) | Trung bình |
| 4.3 | Filter logic: chỉ reply comment liên quan đến sản phẩm | Trung bình |
| 4.4 | Tự động reply comment trên Facebook (Graph API) | Trung bình |
| 4.5 | Cấu hình OBS → Facebook Live RTMP key | Dễ |
| 4.6 | Test end-to-end: comment → AI trả lời trên cả video lẫn FB comment | Cao |

### Yêu cầu tài khoản
- Facebook Developer Account
- Facebook Page (có quyền stream)
- App với permission: `pages_read_engagement`, `pages_manage_posts`, `pages_messaging`

---

## Phase 5 — Web UI Quản lý & Monitoring ⬜ TODO

**Mục đích:** Người vận hành có thể theo dõi và điều chỉnh AI từ xa, không cần mở terminal.

### Tính năng cần xây trên web UI

#### Dashboard (trang chính)
```
┌─────────────────────────────────────────────────────┐
│  🟢 Linh đang live — 1h 23m                        │
│                                                     │
│  Hôm nay:  47 comments   |  38 đã trả lời          │
│  Tỉ lệ:    80.8%         |  Thời gian TB: 4.2s     │
│                                                     │
│  [▶ Live feed comments]                             │
│  14:32 | Nga: "combo có ship không ạ?"              │
│  14:32 | Linh: "Dạ có ạ, freeship đơn từ 300K..."  │
│  14:33 | Hùng: "giá bao nhiêu vậy shop"            │
│  14:33 | Linh: "Combo Nhộng Ong hiện 590K bạn ơi" │
└─────────────────────────────────────────────────────┘
```

#### Trang cấu hình AI
- Chỉnh system prompt / persona Linh trực tiếp trên web
- Upload/thay đổi Q&A knowledge base (qa.csv)
- Chọn giọng TTS (Hoài My / Nam Minh)
- Bật/tắt lip sync

#### Trang cấu hình Avatar
- Thay video avatar (upload mp4 mới)
- Preview video ngay trên web
- Điều chỉnh FPS, kích thước cửa sổ

#### Trang Stream Control
- Bắt đầu/dừng lắng nghe Facebook comment
- Xem RTMP stream status
- Bật/tắt tự động reply

#### Alert & Monitoring
- Cảnh báo khi AI lỗi (Gemini timeout, TTS fail)
- Log các comment chưa được trả lời
- Export lịch sử Q&A ra CSV

### Các task cần làm

| # | Task | Ghi chú |
|---|------|---------|
| 5.1 | Thêm API endpoint thống kê comment | `flask_server.py` |
| 5.2 | Dashboard realtime (WebSocket) | Đã có sẵn WS port 10003 |
| 5.3 | Form chỉnh persona / system prompt | Lưu vào config.json |
| 5.4 | Upload avatar video mới qua web | Lưu vào `avatar/assets/` |
| 5.5 | Stream control panel | Start/stop listener |
| 5.6 | Alert system (email/Telegram) | Khi AI down |

---

## Tổng tiến độ

| Phase | Tên | Key Result | Status | Done |
|-------|-----|-----------|--------|------|
| **1** | AI Sales Host | 1. Khách gõ chat → AI reply bằng giọng nói tiếng Việt (Edge-TTS Hoài My) + icon mấp máy miệng<br>2. AI đóng vai Linh, tư vấn bán Dr.Bee Nhộng Ong 590K với 16 Q&A sản phẩm thực tế<br>3. Toàn bộ UI, system prompt, error message đã Việt hoá — sẵn sàng demo cho khách | ✅ Done | 9/9 |
| **2** | Avatar Video | 1. Cửa sổ video avatar phát vòng lặp liên tục có tiếng, OBS capture được để đưa lên stream<br>2. Khi AI trả lời: dừng video idle, phát audio AI — khi xong tự quay lại vòng lặp<br>3. Audio-video không lệch nhau (audio-clock sync), cửa sổ tự fit màn hình giữ đúng tỉ lệ | ✅ Done | 9/9 |
| **3** | Lip Sync | 1. Khi AI nói, avatar nhép môi khớp từng âm tiết (Wav2Lip) — trông như người thật livestream<br>2. Xử lý async: TTS pipeline không bị block, lip sync chạy nền ~3-15s rồi tự phát<br>3. Audio TTS bị hold đến khi video lip sync ready, tránh double audio | ✅ Code / ⏳ Test | 5/6 |
| **4** | Facebook Live | 1. Tự động đọc comment người xem từ Facebook Livestream realtime qua Graph API webhook<br>2. AI xử lý và reply comment trên Facebook trong vài giây — không cần người trực, 24/7<br>3. OBS stream video avatar lên Facebook Live RTMP, toàn bộ chạy tự động | ⬜ TODO | 0/6 |
| **5** | Web UI Quản lý | 1. Dashboard realtime: xem live feed comment, tỉ lệ reply, thống kê phiên stream<br>2. Quản lý nội dung: chỉnh persona AI, Q&A sản phẩm, thay avatar video — không cần mở terminal<br>3. Alert & monitor: cảnh báo khi AI lỗi, log comment chưa reply, bật/tắt stream từ xa | ⬜ TODO | 0/6 |

**Tổng:** 23/36 tasks hoàn thành (64%)

---

## Milestone để "lên được bản livestream"

```
Hôm nay (Phase 1+2+3 xong):
  → Avatar phát video + tiếng liên tục
  → AI trả lời khi test qua web UI
  → Nhép môi khi AI nói (sau khi cài Wav2Lip)
  → OBS capture được cửa sổ → stream thủ công lên FB

Phase 4 xong:
  → Không cần người điều phối
  → Tự lắng nghe comment FB và tự reply 24/7

Phase 5 xong:
  → Vận hành từ xa hoàn toàn
  → Monitor realtime, nhận alert khi có sự cố
  → ĐÂY LÀ BẢN LIVESTREAM THỰC SỰ PRODUCTION-READY
```
