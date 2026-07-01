# CI/CD Guide - Life Dashboard

## CI/CD là gì?

**CI/CD** = **Continuous Integration / Continuous Deployment** (Tích hợp liên tục / Triển khai liên tục)

Nôm na: **Mỗi khi bạn push code lên GitHub, hệ thống sẽ TỰ ĐỘNG kiểm tra code và deploy lên server.**

Không CI/CD:
```
Viết code → Push GitHub → SSH vào server → Pull code → Build → Restart app
(thủ công, dễ quên, dễ sai)
```

Có CI/CD:
```
Viết code → Push GitHub → ☕ Ngồi chờ → App tự động cập nhật trên server
(tự động, nhất quán, an toàn)
```

---

## Kiến trúc CI/CD của project này

```
┌─────────────┐     push code      ┌──────────────┐
│  Máy của bạn │ ────────────────► │    GitHub     │
└─────────────┘                    └──────┬───────┘
                                          │
                                          │ trigger workflow
                                          │
                              ┌───────────▼────────────┐
                              │   GitHub Actions        │
                              │   (điều phối công việc) │
                              └───────────┬────────────┘
                                          │
                         ┌────────────────┼────────────────┐
                         │                                 │
                         ▼                                 ▼
              ┌──────────────────┐              ┌──────────────────┐
              │   CI (ci.yml)    │              │ Deploy (deploy.yml)│
              │ Chạy trên GitHub │              │ Chạy trên SERVER  │
              │ (ubuntu-latest)  │              │ (self-hosted)     │
              └──────────────────┘              └──────────────────┘
              │ - Cài dependencies│              │ - docker compose  │
              │ - Lint code       │              │   down/build/up   │
              │ - Chạy tests      │              │ - Health check    │
              │ - Thử build       │              │ - Dọn image cũ    │
              └──────────────────┘              └──────────────────┘
```

---

## 2 Workflow của project

### 1. CI (`ci.yml`) - Kiểm tra code

**Khi nào chạy?** Mỗi khi push hoặc tạo PR vào branch `main`/`master`

**Chạy ở đâu?** Trên máy chủ của GitHub (miễn phí)

**Làm gì?**
1. Cài dependencies (`npm ci`)
2. Generate Prisma client
3. Lint - kiểm tra code style
4. Chạy tests
5. Thử build xem có lỗi không

**Mục đích:** Đảm bảo code không bị lỗi trước khi merge.

### 2. Deploy (`deploy.yml`) - Triển khai lên server

**Khi nào chạy?** Chỉ khi push vào branch `main` (hoặc bấm nút chạy thủ công)

**Chạy ở đâu?** Trên server VPS (self-hosted runner)

**Làm gì?**
1. Checkout code mới nhất
2. `docker compose down` - tắt container cũ
3. `docker compose build --no-cache` - build image mới
4. `docker compose up -d` - khởi động container mới
5. Health check - kiểm tra app có chạy được không
6. Dọn dẹp Docker image cũ

---

## Self-hosted Runner là gì?

GitHub Actions cần một **máy tính** để chạy các lệnh. Có 2 loại:

| | GitHub-hosted | Self-hosted |
|---|---|---|
| **Máy** | Máy ảo của GitHub | Server của bạn |
| **Giá** | Miễn phí (giới hạn) | Miễn phí (dùng server sẵn có) |
| **Tốc độ** | Phải tải code, cài deps mỗi lần | Nhanh hơn vì có cache |
| **Quyền** | Không truy cập server bạn | Toàn quyền trên server |
| **Dùng khi** | Chạy tests, lint | Deploy lên chính server đó |

Trong project này:
- **CI** dùng GitHub-hosted (chỉ cần test, không cần server)
- **Deploy** dùng self-hosted (cần chạy `docker compose` trên server)

---

## Bảo mật

Vì repo là **public**, ai cũng đọc được code. Rủi ro: người lạ fork repo, tạo PR chứa lệnh độc → chạy trên server của bạn.

**Cách bảo vệ đã áp dụng:**

- `deploy.yml` chỉ trigger trên `push to main` → người ngoài **không thể** trigger deploy qua PR
- `ci.yml` có chạy trên PR nhưng dùng `ubuntu-latest` (máy GitHub) → **không ảnh hưởng** server của bạn

```yaml
# deploy.yml - AN TOÀN
on:
  push:
    branches: [main]     # Chỉ khi push trực tiếp vào main
  workflow_dispatch:      # Hoặc bấm nút chạy thủ công
jobs:
  deploy:
    runs-on: self-hosted  # Chạy trên server của bạn
```

---

## Cách dùng hàng ngày

### Push code và tự động deploy
```bash
git add .
git commit -m "thêm tính năng X"
git push origin main
```
→ Xong. Chờ 1-2 phút, app tự cập nhật.

### Xem trạng thái workflow
Vào GitHub repo → tab **Actions** → xem workflow đang chạy/thành công/thất bại.

### Chạy deploy thủ công
GitHub repo → **Actions** → chọn **Deploy** → bấm **Run workflow**

### Xem log runner trên server
```bash
cat /home/ubuntu/actions-runner/runner.log
```

### Restart runner (nếu bị dừng)
```bash
cd /home/ubuntu/actions-runner
nohup ./run.sh >> runner.log 2>&1 &
```

---

## Cấu hình hiện tại

| Thành phần | Giá trị |
|---|---|
| Runner location | `/home/ubuntu/actions-runner` |
| Runner name | `life-dashboard-runner` |
| App port | `3800` |
| Auto-start | Crontab `@reboot` |
| Docker Compose | `/home/ubuntu/cuong_dn/life-dashboard/docker-compose.yml` |

---

## Flow tổng thể khi bạn push code

```
1. Bạn: git push origin main
         │
2. GitHub nhận code mới
         │
3. GitHub trigger 2 workflows song song:
         │
         ├── ci.yml (trên máy GitHub)
         │   ├── npm ci
         │   ├── prisma generate
         │   ├── npm run lint
         │   ├── npm test
         │   └── npm run build
         │       → Nếu FAIL: báo lỗi trên GitHub
         │       → Nếu PASS: ✅
         │
         └── deploy.yml (trên server 103.253.20.30)
             ├── git checkout code mới
             ├── docker compose down
             ├── docker compose build --no-cache
             ├── docker compose up -d
             ├── health check (curl localhost:3800)
             └── docker image prune
                 → Nếu FAIL: báo lỗi, container cũ đã bị dừng
                 → Nếu PASS: ✅ App đã cập nhật!
```
