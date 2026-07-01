"""
Sync.so Lip Sync module cho Fay.

Flow:
    audio_path (.mp3/.wav) + avatar_video_path → Sync.so API → output video .mp4

Config trong system.conf:
    syncso_api_key=your_api_key_here
    syncso_avatar_video=./avatar/assets/avatar_idle.mp4

Docs: https://docs.sync.so/
"""
import os
import time
import requests
from utils import util
from utils import config_util as cfg


# Sync.so API endpoints
_API_BASE = "https://api.sync.so/v2"
_GENERATE_URL = f"{_API_BASE}/generate"


def _get_api_key() -> str:
    return getattr(cfg, "syncso_api_key", None) or os.environ.get("SYNCSO_API_KEY", "")


def _get_avatar_video() -> str:
    return getattr(cfg, "syncso_avatar_video", None) or "./avatar/assets/avatar_idle.mp4"


def generate(audio_path: str, output_dir: str = "./samples") -> str | None:
    """
    Gọi Sync.so API để tạo lip sync video.

    Args:
        audio_path: Đường dẫn file audio (.mp3 / .wav)
        output_dir: Thư mục lưu video output

    Returns:
        Đường dẫn file video .mp4 nếu thành công, None nếu lỗi.
    """
    api_key = _get_api_key()
    avatar_video = _get_avatar_video()

    if not api_key:
        util.log(2, "[SyncSo] Thiếu API key — kiểm tra syncso_api_key trong system.conf")
        return None
    if not os.path.exists(audio_path):
        util.log(2, f"[SyncSo] Không tìm thấy file audio: {audio_path}")
        return None
    if not os.path.exists(avatar_video):
        util.log(2, f"[SyncSo] Không tìm thấy video avatar: {avatar_video}")
        util.log(2, "[SyncSo] Tạo thư mục và đặt video idle vào: ./avatar/assets/avatar_idle.mp4")
        return None

    headers = {
        "x-api-key": api_key,
    }

    try:
        # Upload audio + video và tạo job
        with open(audio_path, "rb") as audio_f, open(avatar_video, "rb") as video_f:
            files = {
                "audio": (os.path.basename(audio_path), audio_f, "audio/mpeg"),
                "video": (os.path.basename(avatar_video), video_f, "video/mp4"),
            }
            data = {
                "model": "sync-1.9.0-beta",
            }
            util.log(1, "[SyncSo] Đang gửi request tạo lip sync...")
            resp = requests.post(_GENERATE_URL, headers=headers, files=files, data=data, timeout=60)

        if resp.status_code not in (200, 201):
            util.log(2, f"[SyncSo] Lỗi tạo job {resp.status_code}: {resp.text[:300]}")
            return None

        job = resp.json()
        job_id = job.get("id")
        if not job_id:
            util.log(2, f"[SyncSo] Không nhận được job ID: {job}")
            return None

        util.log(1, f"[SyncSo] Job tạo thành công: {job_id} — đang chờ kết quả...")

        # Poll trạng thái job
        video_url = _poll_job(job_id, api_key)
        if not video_url:
            return None

        # Tải video về
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f"lipsync-{int(time.time() * 1000)}.mp4")
        _download_video(video_url, output_path)

        util.log(1, f"[SyncSo] Lip sync OK → {output_path}")
        return output_path

    except Exception as e:
        util.log(2, f"[SyncSo] Exception: {e}")
        return None


def _poll_job(job_id: str, api_key: str, timeout: int = 120, interval: int = 3) -> str | None:
    """Poll Sync.so job cho đến khi completed hoặc timeout."""
    status_url = f"{_GENERATE_URL}/{job_id}"
    headers = {"x-api-key": api_key}
    deadline = time.time() + timeout

    while time.time() < deadline:
        try:
            resp = requests.get(status_url, headers=headers, timeout=15)
            if resp.status_code != 200:
                util.log(2, f"[SyncSo] Poll lỗi {resp.status_code}: {resp.text[:200]}")
                return None

            data = resp.json()
            status = data.get("status", "")

            if status == "completed":
                # Lấy URL video output
                output = data.get("outputUrl") or data.get("output_url") or ""
                if not output:
                    # Thử tìm trong nested structure
                    output = (data.get("output") or {}).get("url", "")
                if output:
                    return output
                util.log(2, f"[SyncSo] Job completed nhưng không có outputUrl: {data}")
                return None
            elif status in ("failed", "error"):
                util.log(2, f"[SyncSo] Job thất bại: {data.get('error', 'unknown error')}")
                return None
            else:
                util.log(1, f"[SyncSo] Trạng thái: {status} — đợi {interval}s...")

        except Exception as e:
            util.log(2, f"[SyncSo] Poll exception: {e}")

        time.sleep(interval)

    util.log(2, f"[SyncSo] Timeout sau {timeout}s chờ job {job_id}")
    return None


def _download_video(url: str, output_path: str) -> None:
    """Tải video từ URL về local."""
    resp = requests.get(url, timeout=60, stream=True)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
