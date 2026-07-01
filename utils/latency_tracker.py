# -*- coding: utf-8 -*-
"""
Latency tracker — in live progress + summary block khi finish().
"""
import threading
import time
from utils import util

_sessions: dict = {}
_lock = threading.Lock()
_SEP = "─" * 48

# (label hien tai, hint buoc tiep theo)
_NEXT_HINT = {
    "Nhan message":  "→ LLM dang suy nghi + TTS...",
    "TTS":           "→ Dang buffer audio...",
    "Wav2Lip bat dau": "→ Uoc tinh 60-90 giay...",
    "Video bat dau phat": "→ Xong!",
}


def _hint(label: str) -> str:
    for key, hint in _NEXT_HINT.items():
        if key in label:
            return hint
    return ""


def start(conv_id: str, question: str = ""):
    with _lock:
        _sessions[conv_id] = {
            "t0": time.time(),
            "question": question[:60],
            "steps": [],
            "tts_count": 0,
        }
    util.log(1, f"[Progress] Nhan message: \"{question[:50]}\"  {_hint('Nhan message')}")


def step(conv_id: str, label: str):
    with _lock:
        s = _sessions.get(conv_id)
        if not s:
            return
        elapsed = time.time() - s["t0"]
        if "TTS" in label:
            s["tts_count"] += 1
            import re as _re
            m = _re.search(r"\((\d+)", label)
            dur = f"({m.group(1)}ms)" if m else ""
            label = f"TTS chunk {s['tts_count']} xong {dur}".strip()
        s["steps"].append((elapsed, label))
    util.log(1, f"[Progress] +{elapsed:.1f}s  {label}  {_hint(label)}")


def finish(conv_id: str, label: str = "Video bat dau phat"):
    with _lock:
        s = _sessions.pop(conv_id, None)
    if not s:
        return
    total = time.time() - s["t0"]
    util.log(1, f"[Progress] +{total:.1f}s  {label}  {_hint(label)}")

    # Summary block
    lines = [
        f"┌{_SEP}",
        f'│  KHACH: "{s["question"]}"',
        f"│  +0.0s   Nhan message",
    ]
    for elapsed, lbl in s["steps"]:
        lines.append(f"│  +{elapsed:.1f}s{'':3} {lbl}")
    lines.append(f"│  +{total:.1f}s{'':3} {label}")
    lines.append(f"└─ TONG: {total:.1f}s")
    for line in lines:
        util.log(1, f"[Latency] {line}")
