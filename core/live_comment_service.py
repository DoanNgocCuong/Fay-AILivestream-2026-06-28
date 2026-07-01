"""
live_comment_service.py
Dich vu tich hop doc comment tu Facebook Live va TikTok Live.
- Nhan comment tu FacebookLiveReader / TikTokLiveReader
- Priority queue: real comment > proactive monologue
- Push vao Fay AI queue qua WebSocket ws://localhost:10003
  hoac goi truc tiep fay_core.put_interact()

Config trong .env hoac environment:
    LIVE_FB_URL=https://www.facebook.com/.../videos/xxxxx
    LIVE_TIKTOK_ID=@drbee.official
    LIVE_COMMENT_ENABLED=true
"""
import logging
import os
import queue
import threading
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Import readers (graceful - khong crash neu chua cai dep)
try:
    from core.facebook_reader import FacebookLiveReader, LiveComment as FBComment
    _fb_available = True
except ImportError:
    _fb_available = False
    logger.warning("[LiveCommentService] facebook_reader khong kha dung")

try:
    from core.tiktok_reader import TikTokLiveReader, LiveComment as TTComment
    _tt_available = True
except ImportError:
    _tt_available = False
    logger.warning("[LiveCommentService] tiktok_reader khong kha dung")


@dataclass
class PrioritizedComment:
    priority: int      # 0 = cao nhat (real comment), 1 = thap (proactive)
    username: str
    text: str
    source: str        # "facebook" | "tiktok" | "manual"
    timestamp: float


class LiveCommentService:
    """
    Singleton service quan ly doc comment tu tat ca platform livestream.

    Usage:
        svc = LiveCommentService.get_instance()
        svc.start()           # bat dau doc comment
        svc.stop()            # dung
        svc.inject_manual("user", "text")   # inject comment thu cong (test)
    """

    _instance: "LiveCommentService | None" = None
    _lock = threading.Lock()

    def __init__(self):
        self._pq: queue.PriorityQueue = queue.PriorityQueue()
        self._fb_reader: "FacebookLiveReader | None" = None
        self._tt_reader: "TikTokLiveReader | None" = None
        self._running = False
        self._dispatch_thread: threading.Thread | None = None
        self._seq = 0  # tiebreaker cho priority queue
        self._seq_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "LiveCommentService":
        with cls._lock:
            if cls._instance is None:
                cls._instance = LiveCommentService()
            return cls._instance

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(
        self,
        fb_url: str | None = None,
        tiktok_id: str | None = None,
        fb_headless: bool = True,
    ):
        """
        Bat dau service.
        fb_url: URL cua Facebook Live stream (None = lay tu env LIVE_FB_URL)
        tiktok_id: TikTok username (None = lay tu env LIVE_TIKTOK_ID)
        """
        if self._running:
            logger.warning("[LiveCommentService] Da dang chay")
            return

        fb_url = fb_url or os.getenv("LIVE_FB_URL", "")
        tiktok_id = tiktok_id or os.getenv("LIVE_TIKTOK_ID", "")
        enabled = os.getenv("LIVE_COMMENT_ENABLED", "false").lower() == "true"

        if not enabled:
            logger.info("[LiveCommentService] LIVE_COMMENT_ENABLED=false, bo qua")
            return

        self._running = True

        # Facebook reader
        if fb_url and _fb_available:
            self._fb_reader = FacebookLiveReader(live_url=fb_url, headless=fb_headless)
            self._fb_reader.start_polling(callback=self._on_fb_comment)
            logger.info("[LiveCommentService] Facebook reader bat dau: %s", fb_url)
        elif fb_url:
            logger.warning("[LiveCommentService] Facebook URL co nhung reader khong kha dung")

        # TikTok reader
        if tiktok_id and _tt_available:
            self._tt_reader = TikTokLiveReader(unique_id=tiktok_id)
            self._tt_reader.start_polling(callback=self._on_tt_comment)
            logger.info("[LiveCommentService] TikTok reader bat dau: %s", tiktok_id)
        elif tiktok_id:
            logger.warning("[LiveCommentService] TikTok ID co nhung reader khong kha dung")

        # Dispatch thread
        self._dispatch_thread = threading.Thread(
            target=self._dispatch_loop, daemon=True, name="live-dispatch"
        )
        self._dispatch_thread.start()
        logger.info("[LiveCommentService] Service da khoi dong")

    def stop(self):
        """Dung service va tat ca readers."""
        self._running = False
        if self._fb_reader:
            self._fb_reader.stop()
            self._fb_reader = None
        if self._tt_reader:
            self._tt_reader.stop()
            self._tt_reader = None
        if self._dispatch_thread:
            self._dispatch_thread.join(timeout=5)
        logger.info("[LiveCommentService] Da dung")

    def inject_manual(self, username: str, text: str):
        """Inject comment thu cong (vi du tu WebSocket UI)."""
        self._enqueue(username=username, text=text, source="manual", priority=0)

    # ------------------------------------------------------------------
    # Callbacks tu readers
    # ------------------------------------------------------------------

    def _on_fb_comment(self, comment):
        self._enqueue(
            username=comment.username,
            text=comment.text,
            source="facebook",
            priority=0,
        )

    def _on_tt_comment(self, comment):
        self._enqueue(
            username=comment.username,
            text=comment.text,
            source="tiktok",
            priority=0,
        )

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------

    def _enqueue(self, username: str, text: str, source: str, priority: int = 0):
        with self._seq_lock:
            seq = self._seq
            self._seq += 1
        item = PrioritizedComment(
            priority=priority,
            username=username,
            text=text,
            source=source,
            timestamp=time.time(),
        )
        # PriorityQueue sort by (priority, seq) -> real comments truoc
        self._pq.put((priority, seq, item))
        logger.debug("[LiveCommentService] Enqueue [%s/%s]: %s", source, username, text[:40])

    # ------------------------------------------------------------------
    # Dispatch loop - lay tu queue va push vao Fay
    # ------------------------------------------------------------------

    def _dispatch_loop(self):
        while self._running:
            try:
                # Block toi da 1s de co the check _running
                priority, seq, item = self._pq.get(timeout=1.0)
                self._send_to_fay(item)
            except queue.Empty:
                continue
            except Exception as e:
                logger.error("[LiveCommentService] Loi dispatch: %s", e)

    def _send_to_fay(self, item: PrioritizedComment):
        """
        Gui comment vao Fay AI.
        Thu fay_core.put_interact() truoc, fallback WebSocket neu can.
        """
        source_label = {
            "facebook": "📘 Facebook",
            "tiktok": "🎵 TikTok",
            "manual": "💬 Manual",
        }.get(item.source, item.source)

        display_text = f"[{source_label}] {item.username}: {item.text}"
        logger.info("[LiveCommentService] -> Fay: %s", display_text)

        # Method 1: Direct call vao fay_core (prefer, khong can WebSocket)
        try:
            from core import fay_core
            from core.interact import Interact
            interact = Interact(
                interleaver="live_comment",
                interact_type=1,
                data={
                    "user": item.username,
                    "msg": item.text,
                    "source": item.source,
                }
            )
            fay_core.put_interact(interact)
            return
        except Exception as e:
            logger.debug("[LiveCommentService] fay_core.put_interact that bai: %s - thu WebSocket", e)

        # Method 2: WebSocket fallback -> ws://localhost:10003
        try:
            import json
            import websocket  # websocket-client
            ws_url = os.getenv("FAY_WS_URL", "ws://127.0.0.1:10003")
            ws = websocket.create_connection(ws_url, timeout=3)
            payload = json.dumps({
                "interact": {
                    "interleaver": "live_comment",
                    "interact_type": 1,
                    "data": {
                        "user": item.username,
                        "msg": item.text,
                        "source": item.source,
                    }
                }
            }, ensure_ascii=False)
            ws.send(payload)
            ws.close()
        except Exception as e:
            logger.error("[LiveCommentService] WebSocket fallback that bai: %s", e)


# ------------------------------------------------------------------
# Convenience startup function
# ------------------------------------------------------------------

def start_live_comment_service(
    fb_url: str | None = None,
    tiktok_id: str | None = None,
    fb_headless: bool = True,
) -> LiveCommentService:
    """
    Khoi dong LiveCommentService (singleton).
    Goi ham nay tu fay_booter.py hoac main.py.
    """
    svc = LiveCommentService.get_instance()
    svc.start(fb_url=fb_url, tiktok_id=tiktok_id, fb_headless=fb_headless)
    return svc
