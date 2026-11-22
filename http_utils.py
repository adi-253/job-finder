import html
import re

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

TIMEOUT = 20
UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"


def make_session() -> requests.Session:
    """A session with a browser UA and retries (incl. 429 with Retry-After)."""
    s = requests.Session()
    s.headers.update({"User-Agent": UA, "Accept": "application/json, text/html;q=0.9, */*;q=0.8"})
    retry = Retry(
        total=2,
        backoff_factor=3,  # waits ~3s then ~6s
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=None,  # retry POSTs too (all our POSTs are read-only searches)
        # Workday answers 429 with very long Retry-After values. Waiting them out would stall
        # the whole run; failing fast is fine because the next run (15 min later) catches up.
        respect_retry_after_header=False,
    )
    s.mount("https://", HTTPAdapter(max_retries=retry))
    return s


_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")


def html_to_text(s: str | None) -> str:
    if not s:
        return ""
    s = html.unescape(s)
    if "&lt;" in s or "&gt;" in s:  # double-escaped (Greenhouse)
        s = html.unescape(s)
    s = re.sub(r"<(br|/p|/li|/div|/h\d)\s*/?>", "\n", s, flags=re.I)
    s = _TAG.sub(" ", s)
    s = _WS.sub(" ", s)
    return re.sub(r"\n\s*\n+", "\n", s).strip()
