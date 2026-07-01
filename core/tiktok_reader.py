"""
tiktok_reader.py
Doc comment realtime tu TikTok Live bang TikTokLive package (event-based).
- Khong can polling - package su dung WebSocket native cua TikTok
- Filter spam tuong tu facebook_reader
- Push comment vao callback

Requirement: pip install TikTokLive
"""
import logging
import re
import threading
from typing import Callable
from dataclasses import dataclass, field
import time

logger = logging.getLogger(__name__)

_EMOJI_ONLY_RE = re.compile(
    r"^[\U00010000-\U0010ffff\U00002702-\U000027B0\U0001F600-\U0001F64F"
    r"\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF\s]+$"
)


@dataclass
class LiveComment:
    comment_id: str
    username: str
    text: str
    timestamp: float = field(default_factory=time.time)


def _is_spam(text: str) -> bool:
    stripped = text.strip()
    if len(stripped) < 2:
        return True
    if _EMOJI_ONLY_RE.match(stripped):
        return True
    return False


class TikTokLiveReader:
    """
    Doc comment realtime tu TikTok Live.

    Usage:
        reader = TikTokLiveReader(unique_id="@drbee.official")
        reader.start_polling(callback=lambda comment: print(comment.text))
        # ... sau do:
        reader.stop()
    """

    def __init__(self, unique_id: str):
        """
        unique_id: TikTok username, vi du "@drbee.official"
        """
        self._unique_id = unique_id
        self._callback: Callable[[LiveComment], None] | None = None
        self._running = False
        self._thread: threading.Thread | None = None
        self._client = None

    def start_polling(self, callback: Callable[[LiveComment], None]):
        """Bat dau nghe comment. callback duoc goi voi moi LiveComment moi."""
        if self._running:
            logger.warning("[TikTokReader] Da dang chay")
            return
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(
            target=self._run_client, daemon=True, name="tiktok-reader"
        )
        self._thread.start()
        logger.info("[TikTokReader] Bat dau doc comment tu TikTok: %s", self._unique_id)

    def stop(self):
        """Dung nghe comment."""
        self._running = False
        if self._client:
            try:
                # TikTokLive disconnect
                import asyncio
                loop = asyncio.new_event_loop()
                loop.run_until_complete(self._client.disconnect())
                loop.close()
            except Exception:
                pass
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("[TikTokReader] Da dung")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run_client(self):
        """Chay trong thread rieng. Su dung asyncio de chay TikTokLiveClient."""
        import asyncio
        try:
            from TikTokLive import TikTokLiveClient
            from TikTokLive.events import CommentEvent, ConnectEvent, DisconnectEvent
        except ImportError:
            logger.error(
                "[TikTokReader] TikTokLive chua duoc cai. Chay: pip install TikTokLive"
            )
            self._running = False
            return

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            client = TikTokLiveClient(unique_id=self._unique_id)
            self._client = client

            @client.on(ConnectEvent)
            async def on_connect(event: ConnectEvent):
                logger.info("[TikTokReader] Ket noi thanh cong den TikTok Live: %s", self._unique_id)

            @client.on(CommentEvent)
            async def on_comment(event: CommentEvent):
                if not self._running:
                    return
                text = (event.comment or "").strip()
                username = getattr(event.user, "nickname", None) or getattr(event.user, "unique_id", "unknown")
                comment_id = str(getattr(event, "message_id", None) or f"{username}:{text[:30]}")

                if _is_spam(text):
                    return

                comment = LiveComment(
                    comment_id=comment_id,
                    username=username,
                    text=text,
                )
                logger.debug("[TikTokReader] Comment: [%s] %s", username, text)
                if self._callback:
                    try:
                        self._callback(comment)
                    except Exception as e:
                        logger.error("[TikTokReader] Loi callback: %s", e)

            @client.on(DisconnectEvent)
            async def on_disconnect(event: DisconnectEvent):
                logger.warning("[TikTokReader] Ngat ket noi TikTok Live")
                if self._running:
                    # Tu dong reconnect sau 5s
                    await asyncio.sleep(5)
                    logger.info("[TikTokReader] Thu ket noi lai...")
                    try:
                        await client.connect()
                    except Exception as e:
                        logger.error("[TikTokReader] Reconnect that bai: %s", e)

            loop.run_until_complete(client.connect())

        except Exception as e:
            logger.error("[TikTokReader] Loi TikTok client: %s", e)
            self._running = False
        finally:
            loop.close()
