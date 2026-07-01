# GPU Hosting Scripts

Bộ scripts để deploy **VieNeu-TTS + MuseTalk** lên bất kỳ GPU server nào.

## Docker Compose (cách chính thức)

Mỗi service 1 container riêng (giải quyết dứt điểm xung đột Python 3.12/3.11 +
`transformers`/`mmcv` giữa 2 app — xem [runbook](../../docs/02-engineer/5-runbooks/PROB-2026-07-01-gpu-vieneu-musetalk-setup.md)
liệt kê 23 lỗi gặp phải với flow venv thủ công). Xem chi tiết tại
[`docker/README.md`](docker/README.md).

```
1. docker login                              (1 lần, máy local)
2. Double-click docker\build-and-push.bat    (build + push lên Docker Hub)
3. Double-click deploy_docker_registry.bat   (server pull + up -d)
```

Fallback (build thẳng trên server, không qua registry): `Double-click deploy_docker.bat`

## Flow venv cũ — đã chuyển vào `CKP/`

Flow cũ (cài trực tiếp qua venv, không dùng Docker) đã ngừng dùng vì gây 23 lỗi
conflict Python 3.11/3.12 (xem runbook). Code vẫn giữ lại tham khảo tại
[`CKP/`](CKP/) — **chưa được kiểm chứng đồng bộ với flow hiện tại**, không dùng
cho deploy mới trừ khi Docker/nvidia-container-toolkit không cài được trên server.

---

## Cấu trúc

```
scripts/hosting/
├── deploy_docker_registry.bat  ← Khuyến nghị: server pull image từ Docker Hub + up -d
├── deploy_docker.bat           ← Fallback: upload + docker compose up -d --build (build trên server)
├── docker/                     ← Dockerfile, docker-compose.yml, build-and-push.bat (xem docker/README.md)
└── CKP/                        ← Flow venv cũ (archive, không dùng cho deploy mới)
    ├── deploy.bat
    ├── ssh.bat
    ├── install.sh
    ├── start.sh
    ├── stop.sh
    ├── status.sh
    ├── download_models.sh
    └── setup_musetalk_venv.sh
```

---

## Ports

| Service | Port | URL |
|---------|------|-----|
| VieNeu-TTS | 7860 | `http://<GPU_HOST>:7860` |
| MuseTalk | 8080 | `http://<GPU_HOST>:8080` |

---

## Server hiện tại

| Thông tin | Giá trị |
|-----------|---------|
| Host | n2.ckey.vn |
| SSH Port | 1688 |
| GPU | RTX 3090 24GB |
| Giá | 5,649 VND/giờ |
| Hết hạn | 06-07-2026 16:41:20 |
