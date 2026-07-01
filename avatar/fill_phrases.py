"""
Fill phrase system — pre-computes lipsync videos for short transition phrases.

Flow:
  [Startup]       precompute_async() → TTS + Wav2Lip cho ca 2 phrase, cache ra disk
  [Comment den]   play_thinking()    → phat fill_thinking.mp4 NGAY LAP TUC (co nhep moi)
  [After main]    get_closing_path() → tra path fill_closing.mp4 de play_lipsync() chay tiep

Ca 2 phrase deu TINH (khong co ten khach) nen pre-compute duoc.
Ten khach: hien thi tren overlay/UI, khong the them vao lipsync pre-computed.
"""
import asyncio
import hashlib
import os
import threading
import time

from utils import util

CACHE_DIR = os.path.join(os.path.dirname(__file__), "assets", "fill_cache")

PHRASES = {
    "thinking": "Linh thấy anh chị có comment. Anh chị đợi Linh chút, Linh sẽ trả lời anh chị ạ.",
    "closing":  "Linh xin phép quay lại tư vấn sản phẩm tiếp ạ.",
}

VOICE = "vi-VN-HoaiMyNeural"

_cache: dict[str, str] = {}   # key → mp4 absolute path
_lock = threading.Lock()
_ready_event = threading.Event()  # set khi tat ca phrase da san sang


def precompute_async():
    """Khoi dong background thread pre-compute. Tra ve ngay."""
    os.makedirs(CACHE_DIR, exist_ok=True)
    t = threading.Thread(target=_precompute_all, daemon=True, name="FillPhrasePrecompute")
    t.start()


def wait_until_ready(timeout: float = 300) -> bool:
    """Block cho den khi tat ca fill phrase da san sang (hoac timeout).
    Returns True neu san sang, False neu timeout.
    """
    return _ready_event.wait(timeout=timeout)


def is_ready(key: str) -> bool:
    with _lock:
        path = _cache.get(key)
    return bool(path and os.path.exists(path))


def get_path(key: str) -> str | None:
    with _lock:
        return _cache.get(key)


def play_thinking():
    """Phat fill phrase 'thinking' neu da cached (co lipsync). Non-blocking."""
    path = get_path("thinking")
    if path and os.path.exists(path):
        from avatar.video_display import get_display
        util.log(1, "[FillPhrase] [thinking] Phat ngay lap tuc: 'Linh thay anh chi co comment...' (co nhep moi)")
        get_display().play_lipsync(path)
    else:
        util.log(1, "[FillPhrase] [thinking] Chua san sang (dang pre-compute o nen) — bo qua")


def get_closing_path() -> str | None:
    """Tra path fill phrase 'closing' neu da cached, else None."""
    return get_path("closing")


# ---------------------------------------------------------------------------
# Internal
# ---------------------------------------------------------------------------

def _precompute_all():
    from avatar import config as _cfg
    wav2lip_ok = (
        os.path.exists(_cfg.WAV2LIP_INFERENCE)
        and os.path.exists(_cfg.WAV2LIP_CHECKPOINT)
    )

    for key, text in PHRASES.items():
        mp4_path = os.path.join(CACHE_DIR, f"fill_{key}.mp4")
        wav_path = os.path.join(CACHE_DIR, f"fill_{key}.wav")
        hash_path = os.path.join(CACHE_DIR, f"fill_{key}.hash")
        text_hash = hashlib.md5(f"{text}|{VOICE}".encode()).hexdigest()

        # Neu cache ton tai nhung text da thay doi → xoa cache cu
        if os.path.exists(mp4_path):
            cached_hash = ""
            if os.path.exists(hash_path):
                try:
                    with open(hash_path) as f:
                        cached_hash = f.read().strip()
                except Exception:
                    pass
            if cached_hash == text_hash:
                with _lock:
                    _cache[key] = mp4_path
                util.log(1, f"[FillPhrase] [{key}] Loaded tu disk cache → san sang ngay")
                continue
            else:
                util.log(1, f"[FillPhrase] [{key}] Text thay doi → xoa cache cu, recompute...")
                for f in [mp4_path, wav_path, hash_path]:
                    try:
                        os.remove(f)
                    except Exception:
                        pass

        if not wav2lip_ok:
            util.log(1, f"[FillPhrase] [{key}] Wav2Lip chua san sang — bo qua pre-compute")
            continue

        util.log(1, f"[FillPhrase] [{key}] Pre-compute bat dau: TTS + Wav2Lip...")
        t0 = time.time()

        # TTS
        if not os.path.exists(wav_path):
            if not _tts(text, wav_path):
                util.log(2, f"[FillPhrase] [{key}] TTS that bai")
                continue

        # Wav2Lip
        face = _get_face()
        if not face:
            util.log(2, "[FillPhrase] Khong tim thay avatar face input")
            continue

        from avatar.lip_sync import _run_wav2lip
        ok = _run_wav2lip(face, wav_path, mp4_path)
        elapsed = round(time.time() - t0, 1)

        if ok:
            with _lock:
                _cache[key] = mp4_path
            try:
                with open(hash_path, "w") as f:
                    f.write(text_hash)
            except Exception:
                pass
            util.log(1, f"[FillPhrase] [{key}] Pre-compute xong ({elapsed}s) → da cache vao disk")
        else:
            util.log(2, f"[FillPhrase] [{key}] Wav2Lip that bai sau {elapsed}s")

    # Tat ca phrase da xu ly xong → set ready (ke ca neu 1 so phrase that bai)
    _ready_event.set()
    ready_keys = [k for k in PHRASES if is_ready(k)]
    util.log(1, f"[FillPhrase] San sang: {ready_keys}/{list(PHRASES.keys())} → cho phep livestream bat dau")


def _tts(text: str, out_path: str) -> bool:
    try:
        import edge_tts

        async def _run():
            communicate = edge_tts.Communicate(text, VOICE)
            await communicate.save(out_path)

        asyncio.run(_run())
        return os.path.exists(out_path)
    except Exception as e:
        util.log(2, f"[FillPhrase] TTS error: {e}")
        return False


def _get_face() -> str | None:
    from avatar import config as _cfg
    if os.path.exists(_cfg.AVATAR_VIDEO_PATH):
        return _cfg.AVATAR_VIDEO_PATH
    if os.path.exists(_cfg.AVATAR_IMAGE_PATH):
        return _cfg.AVATAR_IMAGE_PATH
    return None
