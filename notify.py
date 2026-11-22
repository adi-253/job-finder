"""Telegram alerts via the Bot API. Needs TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID in the environment."""
import html
import os
import time
from datetime import datetime

import requests

MAX_SINGLE = 15  # above this, remaining jobs are grouped into digest messages


def _send(text: str) -> None:
    token, chat = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat:
        print("[telegram not configured] " + text.replace("\n", " | "))
        return
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=20,
    )
    if r.status_code == 429:  # flood control: wait as told, then retry once
        time.sleep(r.json().get("parameters", {}).get("retry_after", 5))
        r = requests.post(r.request.url, data=r.request.body, headers=r.request.headers, timeout=20)
    r.raise_for_status()
    time.sleep(1)  # Telegram allows ~1 message/second per chat


def _when(posted) -> str:
    """'2026-11-20T07:17:16+00:00' -> 'Posted 20 Nov'; other formats ('Posted Today') pass through."""
    try:
        return "Posted " + datetime.fromisoformat(str(posted).replace("Z", "+00:00")).strftime("%d %b")
    except ValueError:
        return str(posted)


def _fmt(job) -> str:
    e = html.escape
    lines = [f"🆕 <b>{e(job.company)}</b> · {e(job.title)}", f"📍 {e(job.location)}"]
    if job.posted:
        lines.append(f"🕒 {e(_when(job.posted))}")
    lines.append(f'🔗 <a href="{e(job.url, quote=True)}">Apply</a>')
    return "\n".join(lines)


def send_jobs(jobs) -> None:
    for job in jobs[:MAX_SINGLE]:
        _send(_fmt(job))
    rest = jobs[MAX_SINGLE:]
    chunk = ""
    for job in rest:
        block = _fmt(job) + "\n\n"
        if len(chunk) + len(block) > 3800:  # Telegram limit is 4096 chars
            _send(chunk)
            chunk = ""
        chunk += block
    if chunk:
        _send(chunk)


def send_text(text: str) -> None:
    _send(html.escape(text))
