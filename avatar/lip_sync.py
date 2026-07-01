"""
Wav2Lip processor — chạy inference async, không block TTS pipeline.

Buffering mode: gom TẤT CẢ audio chunks của 1 conversation (theo conversation_id),
khi nhận is_last=True thì concatenate thành 1 WAV dài → chạy Wav2Lip 1 lần → 1 video liền mạch.

Queue: [wav1, wav2, ...] → concat.wav → Wav2Lip → lipsync video → VideoDisplay.play_lipsync()
"""
import os
import queue
import shutil
import subprocess
import sys
import threading
import time
import wave

from avatar import config
from utils import util


_job_queue: queue.Queue = queue.Queue()  # items: (audio_path, is_last)
_worker_thread: threading.Thread | None = None
_started = False
_lock = threading.Lock()

# Buffer gom audio theo conversation_id — chỉ submit Wav2Lip khi is_last=True
_conv_audio_buffers: dict[str, list[str]] = {}
_buffer_lock = threading.Lock()


def submit(audio_path: str, is_last: bool = True, conversation_id: str = "default"):
    """Đưa audio vào buffer. Chỉ chạy Wav2Lip khi is_last=True (toàn bộ response đã sẵn sàng).

    is_last=False: gom audio vào buffer, chưa xử lý.
    is_last=True : concatenate toàn bộ buffer → submit 1 job Wav2Lip duy nhất.
    """
    if not _is_wav2lip_available():
        util.log(2, "[LipSync] Wav2Lip chưa cài, bỏ qua lip sync. Xem avatar/README.md")
        return
    _ensure_started()

    key = conversation_id or "default"

    with _buffer_lock:
        if key not in _conv_audio_buffers:
            _conv_audio_buffers[key] = []
        if audio_path and os.path.exists(audio_path):
            _conv_audio_buffers[key].append(audio_path)

        if not is_last:
            util.log(1, f"[LipSync] Buffer +1 audio ({len(_conv_audio_buffers[key])} chunks) conv={key[:8]}")
            return

        # is_last=True → lấy buffer ra và clear
        chunks = _conv_audio_buffers.pop(key, [])

    util.log(1, f"[LipSync] is_last=True → xử lý {len(chunks)} chunks cho conv={key[:8]}")

    if not chunks:
        util.log(2, "[LipSync] is_last=True nhưng buffer rỗng, bỏ qua")
        return

    # Ghép tất cả chunks thành 1 WAV
    if len(chunks) == 1:
        merged_path = chunks[0]
        util.log(1, f"[LipSync] 1 chunk duy nhất → dùng trực tiếp: {os.path.basename(merged_path)}")
    else:
        merged_path = os.path.join(
            config.OUTPUT_DIR,
            f"merged_{key[:8]}_{int(time.time() * 1000)}.wav"
        )
        ok = _concatenate_wavs(chunks, merged_path)
        if not ok:
            util.log(2, "[LipSync] Ghép WAV thất bại → dùng chunk cuối cùng")
            merged_path = chunks[-1]
        else:
            util.log(1, f"[LipSync] Đã ghép {len(chunks)} chunks → {os.path.basename(merged_path)}")

    util.log(1, f"[LipSync] → đưa job vào queue (qsize trước={_job_queue.qsize()})")
    _job_queue.put((merged_path, True, conversation_id or "default"))
    util.log(1, f"[LipSync] → job trong queue: {_job_queue.qsize()}")


def _concatenate_wavs(wav_paths: list[str], output_path: str) -> bool:
    """Ghép nhiều file WAV thành 1 file duy nhất (cùng sample rate/channels)."""
    valid = [p for p in wav_paths if p and os.path.exists(p)]
    if not valid:
        return False
    if len(valid) == 1:
        shutil.copy2(valid[0], output_path)
        return True
    try:
        frames_data = []
        params = None
        for path in valid:
            with wave.open(path, 'rb') as wf:
                if params is None:
                    params = wf.getparams()
                frames_data.append(wf.readframes(wf.getnframes()))
        if params is None:
            return False
        with wave.open(output_path, 'wb') as out:
            out.setparams(params)
            for chunk in frames_data:
                out.writeframes(chunk)
        return os.path.exists(output_path)
    except Exception as e:
        util.log(2, f"[LipSync] Lỗi ghép WAV: {e}")
        return False


def _is_wav2lip_available() -> bool:
    return (
        os.path.exists(config.WAV2LIP_INFERENCE)
        and os.path.exists(config.WAV2LIP_CHECKPOINT)
    )


def _get_face_input() -> str | None:
    if os.path.exists(config.AVATAR_VIDEO_PATH):
        return config.AVATAR_VIDEO_PATH
    if os.path.exists(config.AVATAR_IMAGE_PATH):
        return config.AVATAR_IMAGE_PATH
    return None


def _ensure_started():
    global _worker_thread, _started
    with _lock:
        if not _started:
            _worker_thread = threading.Thread(target=_worker_loop, daemon=True)
            _worker_thread.start()
            _started = True


def _worker_loop():
    from avatar.video_display import get_display

    util.log(1, "[LipSync] Worker thread started — sẵn sàng nhận job")
    while True:
        try:
            job = _job_queue.get(timeout=5)
        except queue.Empty:
            continue

        util.log(1, f"[LipSync] Worker nhận job từ queue")
        audio_path, is_last, conv_id = job if len(job) == 3 else (*job, "default")

        # Convert to absolute path — Wav2Lip chạy với cwd khác nên relative path sẽ sai
        audio_path = os.path.abspath(audio_path)

        if not os.path.exists(audio_path):
            util.log(2, f"[LipSync] Audio không tồn tại: {audio_path}")
            continue

        face_input = _get_face_input()
        if not face_input:
            util.log(2, "[LipSync] Chưa có file avatar → fallback phát audio trực tiếp")
            _fallback_play_audio(audio_path)
            continue

        output_path = os.path.join(
            config.OUTPUT_DIR,
            f"lipsync_{int(time.time() * 1000)}.mp4"
        )

        util.log(1, f"[Buoc 1/3] Dang nhep moi... (Wav2Lip xu ly, CPU mat ~60-120 giay)")
        try:
            import utils.latency_tracker as _lt
            _lt.step(conv_id, "Wav2Lip bat dau")
        except Exception:
            pass
        t0 = time.time()

        success = _run_wav2lip_with_progress(face_input, audio_path, output_path)

        if success:
            elapsed = round(time.time() - t0, 1)
            util.log(1, f"[Buoc 2/3] Nhep moi xong ({elapsed}s) → dang phat...")
            closing_path = None
            if is_last:
                from avatar import fill_phrases
                closing_path = fill_phrases.get_closing_path()
                if closing_path:
                    util.log(1, "[Buoc 3/3] Phat: main response → closing phrase")
                else:
                    util.log(1, "[Buoc 3/3] Phat: main response (closing chua cache xong)")
            try:
                import utils.latency_tracker as _lt
                _lt.finish(conv_id)
            except Exception:
                pass
            get_display().play_lipsync(output_path, follow_up_path=closing_path)
        else:
            util.log(2, "[LipSync] Wav2Lip that bai → phat audio truc tiep (khong co nhep moi)")
            _fallback_play_audio(audio_path)


def _fallback_play_audio(audio_path: str):
    """Phát TTS audio trực tiếp khi Wav2Lip fail — khách vẫn nghe được response.
    Dùng pygame.mixer.Sound (channel riêng) để không đụng idle video music channel.
    """
    try:
        import pygame
        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
        wav_path = audio_path
        # Nếu không phải wav, dùng ffmpeg convert
        if not audio_path.lower().endswith('.wav'):
            from avatar.video_display import _extract_audio_wav
            converted = _extract_audio_wav(audio_path)
            if converted:
                wav_path = converted
        sound = pygame.mixer.Sound(wav_path)
        channel = sound.play()
        if channel:
            # Block cho đến khi audio xong (đang trong worker thread nên OK)
            while channel.get_busy():
                time.sleep(0.1)
    except Exception as e:
        util.log(2, f"[LipSync] Fallback audio thất bại: {e}")


def _get_env_with_ffmpeg() -> dict:
    """Trả về environ với ffmpeg từ imageio trong PATH."""
    env = os.environ.copy()
    try:
        import imageio_ffmpeg
        ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
        env['PATH'] = ffmpeg_dir + os.pathsep + env.get('PATH', '')
    except Exception:
        pass
    return env


def _run_wav2lip_with_progress(face: str, audio: str, output: str) -> bool:
    """Chạy Wav2Lip và hiển thị progress % thực từ tqdm output."""
    import re as _re

    cmd = [
        sys.executable,
        config.WAV2LIP_INFERENCE,
        "--checkpoint_path", config.WAV2LIP_CHECKPOINT,
        "--face", face,
        "--audio", audio,
        "--outfile", output,
        "--resize_factor", "4",
        "--nosmooth",
    ]
    try:
        proc = subprocess.Popen(
            cmd,
            cwd=config.WAV2LIP_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # gom cả stderr vào stdout để đọc tqdm
            text=True,
            encoding="utf-8",
            errors="replace",
            env=_get_env_with_ffmpeg(),
        )

        last_pct = -1
        stderr_tail = []

        for line in proc.stdout:
            line_s = line.rstrip()
            if line_s:
                stderr_tail.append(line_s)
                if len(stderr_tail) > 50:
                    stderr_tail.pop(0)

            # tqdm dùng \r để overwrite — split theo \r để lấy frame cuối
            for part in line.split("\r"):
                part = part.strip()
                if not part:
                    continue
                # Tìm pattern: "50%|..." hoặc "240/480"
                m_pct = _re.search(r"(\d+)%\|", part)
                m_frac = _re.search(r"(\d+)/(\d+)\s*\[([^\]]+)<([^\]]+)", part)
                if m_pct and m_frac:
                    pct = int(m_pct.group(1))
                    cur, total = int(m_frac.group(1)), int(m_frac.group(2))
                    elapsed_str = m_frac.group(3).strip()
                    eta_str = m_frac.group(4).strip()
                    bar = ("█" * (pct // 10)).ljust(10, "░")
                    if pct != last_pct and pct % 10 == 0:  # log mỗi 10%
                        util.log(1, f"[Wav2Lip] {pct:3d}% |{bar}| {cur}/{total}  elapsed={elapsed_str}  ETA={eta_str}")
                        last_pct = pct

        proc.wait(timeout=300)

        if proc.returncode != 0:
            util.log(2, f"[Wav2Lip] Loi (exit {proc.returncode}): {stderr_tail[-3:]}")
            return False
        return os.path.exists(output)

    except subprocess.TimeoutExpired:
        proc.kill()
        util.log(2, "[Wav2Lip] Timeout (>300s)")
        return False
    except Exception as e:
        util.log(2, f"[Wav2Lip] Exception: {e}")
        return False


def _run_wav2lip(face: str, audio: str, output: str) -> bool:
    cmd = [
        sys.executable,
        config.WAV2LIP_INFERENCE,
        "--checkpoint_path", config.WAV2LIP_CHECKPOINT,
        "--face", face,
        "--audio", audio,
        "--outfile", output,
        "--resize_factor", "4",  # CPU-friendly: giảm resolution → nhanh hơn ~4x
        "--nosmooth",
    ]
    try:
        result = subprocess.run(
            cmd,
            cwd=config.WAV2LIP_DIR,
            capture_output=True,
            text=True,
            timeout=300,
            env=_get_env_with_ffmpeg(),
        )
        if result.returncode != 0:
            util.log(2, f"[LipSync] Wav2Lip error: {result.stderr[-500:]}")
            return False
        return os.path.exists(output)
    except subprocess.TimeoutExpired:
        util.log(2, "[LipSync] Wav2Lip timeout (>120s)")
        return False
    except Exception as e:
        util.log(2, f"[LipSync] Exception: {e}")
        return False
