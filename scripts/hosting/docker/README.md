# Docker Compose — VieNeu-TTS + MuseTalk

Thay thế cho flow venv thủ công ở `scripts/hosting/install.sh` (23 lỗi đã gặp — xem
[runbook](../../../docs/02-engineer/5-runbooks/PROB-2026-07-01-gpu-vieneu-musetalk-setup.md)).
Mỗi service 1 container riêng (Python 3.12 cho VieNeu, Python 3.11 cho MuseTalk — giải quyết
dứt điểm xung đột `transformers`/`mmcv` giữa 2 app), share chung 1 GPU.

Flow cũ (`../install.sh` + venv) vẫn giữ nguyên làm fallback nếu Docker không khả dụng trên server.

## Cấu trúc

```
docker/
├── docker-compose.yml       ← build local (dev)
├── docker-compose.prod.yml  ← pull-only, dùng để deploy lên server (không cần Dockerfile)
├── Dockerfile.vieneu
├── Dockerfile.musetalk
├── entrypoint-vieneu.sh
├── entrypoint-musetalk.sh
├── bootstrap-docker.sh       ← chạy 1 lần/server mới
├── build-and-push.bat        ← build local + push lên Docker Hub
└── .dockerignore
```

## Cách A (khuyến nghị): Build local, push Docker Hub, server chỉ pull

Nhanh nhất vì server không phải build lại (tránh build MuseTalk ~15-20 phút mỗi lần deploy).

```
# 1. Máy local (Windows), 1 lần: docker login (đăng nhập Docker Hub)
docker login

# 2. Build 2 image + push lên hub.docker.com/u/doanngoccuong
Double-click scripts\hosting\docker\build-and-push.bat

# 3. Deploy lên GPU server (chỉ upload docker-compose.prod.yml, không cần Dockerfile)
Double-click scripts\hosting\deploy_docker_registry.bat
```

Image là **public** trên Docker Hub (`doanngoccuong/fay-vieneu-tts`, `doanngoccuong/fay-musetalk`)
→ server pull không cần `docker login`. Mỗi khi sửa Dockerfile/entrypoint: chạy lại
`build-and-push.bat` rồi `deploy_docker_registry.bat` để cập nhật server.

## Cách B (fallback): Build ngay trên GPU server

```bash
# 1. Upload thư mục docker/ lên server (hoặc dùng scripts/hosting/deploy_docker.bat từ Windows)
scp -r -P <SSH_PORT> scripts/hosting/docker root@<GPU_HOST>:/workspace/hosting-docker

# 2. SSH vào, bootstrap Docker + nvidia-container-toolkit (idempotent, skip nếu đã có)
ssh -p <SSH_PORT> root@<GPU_HOST>
cd /workspace/hosting-docker
bash bootstrap-docker.sh

# 3. Build + chạy
docker compose up -d --build
```

Dùng khi chưa muốn push lên Docker Hub hoặc cần debug build ngay trên server.

Lần đầu chạy (cả 2 cách), MuseTalk sẽ tự tải model weights (~5GB) vào `./models/musetalk`
(bind mount) — lần sau restart container không phải tải lại.

## Quản lý

```bash
docker compose ps                 # trạng thái 2 container
docker compose logs -f vieneu-tts # xem log
docker compose logs -f musetalk
docker compose restart musetalk
docker compose down               # dừng (giữ volume ./models)
```

## Rollback

`build-and-push.bat` giờ push cả tag `latest` lẫn tag theo git short-sha (vd `a1b2c3d`).
Muốn rollback về bản cũ trên server:

```bash
# Trên server, trong thư mục docker-compose.prod.yml
IMAGE_TAG=<git-sha-cu> docker compose pull
IMAGE_TAG=<git-sha-cu> docker compose up -d
# hoặc ghi cố định vào file .env cùng thư mục: echo "IMAGE_TAG=<git-sha-cu>" > .env
```

## Ports (giữ nguyên như flow cũ — không cần sửa `.env`/`system.conf`)

| Service | Port | URL |
|---------|------|-----|
| VieNeu-TTS | 7860 | `http://<GPU_HOST>:7860` |
| MuseTalk | 8080 | `http://<GPU_HOST>:8080` |

## Verify

```bash
docker compose config                                                     # validate YAML
docker exec vieneu-tts python3 -c "import torch; print(torch.cuda.is_available())"
docker exec musetalk python3 -c "from mmpose.apis import inference_topdown; print('OK')"
curl http://localhost:7860/
curl http://localhost:8080/
nvidia-smi   # 2 process, tổng VRAM < 24GB
```

## VRAM budget (RTX 3090 24GB)

VieNeu-TTS (~1-3GB) + MuseTalk (UNet+VAE+whisper+face models, ~4-6GB) chạy song song trên
cùng 1 GPU thoải mái. Nếu sau này thêm model thứ 3, kiểm tra lại tổng VRAM trước khi thêm vào
compose file này.
