"""
facebook_reader.py
Doc comment realtime tu Facebook Live bang undetected-chromedriver.
- Poll DOM moi 2s
- Dedup bang comment ID
- Filter spam (all-emoji, qua ngan)
- Push comment vao callback
"""
import re
import time
import threading
import logging
from typing import Callable
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# Regex kiem tra xem string co chi toan emoji/space khong
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
    """Loc spam: chi emoji, qua ngan, hoac rong."""
    stripped = text.strip()
    if len(stripped) < 2:
        return True
    if _EMOJI_ONLY_RE.match(stripped):
        return True
    return False


def _try_import_driver():
    """Import undetected-chromedriver. Raise ImportError neu chua cai."""
    try:
        import undetected_chromedriver as uc
        return uc
    except ImportError as e:
        raise ImportError(
            "undetected-chromedriver chua duoc cai. Chay: pip install undetected-chromedriver"
        ) from e


class FacebookLiveReader:
    """
    Doc comment realtime tu mot Facebook Live stream.

    Usage:
        reader = FacebookLiveReader(live_url="https://www.facebook.com/...")
        reader.start_polling(callback=lambda comment: print(comment.text))
        # ... sau do:
        reader.stop()
    """

    POLL_INTERVAL = 2.0  # giay giua moi lan poll
    MAX_SEEN_IDS = 5000  # gioi han bo nho de-dup

    def __init__(self, live_url: str, headless: bool = True):
        self._live_url = live_url
        self._headless = headless
        self._callback: Callable[[LiveComment], None] | None = None
        self._seen_ids: set[str] = set()
        self._running = False
        self._thread: threading.Thread | None = None
        self._driver = None

    def start_polling(self, callback: Callable[[LiveComment], None]):
        """Bat dau poll comment. callback duoc goi voi moi LiveComment moi."""
        if self._running:
            logger.warning("[FacebookReader] Da dang chay")
            return
        self._callback = callback
        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True, name="fb-reader")
        self._thread.start()
        logger.info("[FacebookReader] Bat dau doc comment tu: %s", self._live_url)

    def stop(self):
        """Dung polling va dong browser."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._close_driver()
        logger.info("[FacebookReader] Da dung")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _poll_loop(self):
        try:
            self._driver = self._create_driver()
            self._driver.get(self._live_url)
            # Cho trang load
            time.sleep(5)
            logger.info("[FacebookReader] Da mo Facebook Live page")
        except Exception as e:
            logger.error("[FacebookReader] Loi khoi tao browser: %s", e)
            self._running = False
            return

        while self._running:
            try:
                comments = self._scrape_comments()
                for c in comments:
                    if c.comment_id not in self._seen_ids:
                        self._seen_ids.add(c.comment_id)
                        # Gioi han bo nho
                        if len(self._seen_ids) > self.MAX_SEEN_IDS:
                            self._seen_ids = set(list(self._seen_ids)[-self.MAX_SEEN_IDS // 2:])
                        if not _is_spam(c.text):
                            logger.debug("[FacebookReader] Comment moi: [%s] %s", c.username, c.text)
                            if self._callback:
                                try:
                                    self._callback(c)
                                except Exception as cb_err:
                                    logger.error("[FacebookReader] Loi callback: %s", cb_err)
            except Exception as e:
                logger.warning("[FacebookReader] Loi poll: %s", e)

            time.sleep(self.POLL_INTERVAL)

        self._close_driver()

    def _create_driver(self):
        uc = _try_import_driver()
        options = uc.ChromeOptions()
        if self._headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--mute-audio")
        options.add_argument("--lang=vi")
        driver = uc.Chrome(options=options, use_subprocess=True)
        return driver

    def _scrape_comments(self) -> list[LiveComment]:
        """
        Lay comment tu DOM cua Facebook Live page.
        Facebook hay thay doi DOM nen dung nhieu selector de backup.
        """
        if not self._driver:
            return []

        # Cac CSS selector co the tim thay comment container
        # Facebook hay update DOM nen danh sach nay can duoc maintain
        selectors = [
            "[data-testid='UFI2CommentsList/root_depth_0'] [data-testid='UFI2Comment/root']",
            "div[aria-label*='comment']",
            ".x1iorvi4",  # internal class (hay thay doi)
        ]

        comments: list[LiveComment] = []

        for selector in selectors:
            try:
                elements = self._driver.find_elements("css selector", selector)
                if elements:
                    for el in elements:
                        comment = self._parse_comment_element(el)
                        if comment:
                            comments.append(comment)
                    break
            except Exception:
                continue

        # Fallback: thu lay bang JavaScript
        if not comments:
            comments = self._scrape_via_js()

        return comments

    def _parse_comment_element(self, element) -> LiveComment | None:
        """Parse mot comment element thanh LiveComment object."""
        try:
            # Lay text noi dung
            text_el = None
            for text_selector in ["[dir='auto']", "span[lang]", "span"]:
                try:
                    text_el = element.find_element("css selector", text_selector)
                    if text_el and text_el.text.strip():
                        break
                except Exception:
                    continue

            if not text_el or not text_el.text.strip():
                return None

            text = text_el.text.strip()

            # Lay username
            username = "unknown"
            try:
                name_el = element.find_element("css selector", "a[href*='/user/'], a[href*='profile.php']")
                username = name_el.text.strip() or "unknown"
            except Exception:
                pass

            # Tao unique ID tu noi dung + username (khong co comment_id that tu DOM)
            import hashlib
            raw_id = f"{username}:{text[:50]}"
            comment_id = hashlib.md5(raw_id.encode()).hexdigest()

            return LiveComment(comment_id=comment_id, username=username, text=text)
        except Exception:
            return None

    def _scrape_via_js(self) -> list[LiveComment]:
        """Fallback: lay comment bang JavaScript execution."""
        try:
            js = """
            var comments = [];
            var spans = document.querySelectorAll('span[dir="auto"]');
            for (var i = 0; i < Math.min(spans.length, 50); i++) {
                var text = spans[i].innerText;
                if (text && text.length > 2 && text.length < 500) {
                    comments.push({text: text, username: 'user_' + i});
                }
            }
            return comments;
            """
            raw = self._driver.execute_script(js) or []
            result = []
            import hashlib
            for item in raw:
                text = item.get("text", "").strip()
                username = item.get("username", "unknown")
                if text:
                    cid = hashlib.md5(f"{username}:{text[:50]}".encode()).hexdigest()
                    result.append(LiveComment(comment_id=cid, username=username, text=text))
            return result
        except Exception:
            return []

    def _close_driver(self):
        if self._driver:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None
