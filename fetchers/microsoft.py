"""Microsoft careers (apply.careers.microsoft.com, Eightfold 'pcsx' API), newest first."""
from datetime import datetime, timezone

from http_utils import TIMEOUT, html_to_text
from models import Job

BASE = "https://apply.careers.microsoft.com"


def fetch(c, s):
    jobs = []
    for p in range(c.get("pages", 4)):
        r = s.get(f"{BASE}/api/pcsx/search", timeout=TIMEOUT, params={
            "domain": "microsoft.com", "query": c.get("query", "software engineer"),
            "location": "India", "start": p * 10, "sort_by": "timestamp",
        })
        r.raise_for_status()
        data = r.json().get("data") or {}
        for j in data.get("positions", []):
            ts = j.get("postedTs")
            jobs.append(Job(
                company=c["name"],
                id=str(j["id"]),
                title=j.get("name", "").strip(),
                location=" / ".join(dict.fromkeys(j.get("locations", []))),
                url=BASE + j.get("positionUrl", ""),
                posted=datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else "",
            ))
        if (p + 1) * 10 >= data.get("count", 0):
            break
    return jobs


def describe(c, s, job):
    r = s.get(f"{BASE}/api/pcsx/position_details", timeout=TIMEOUT,
              params={"position_id": job.id, "domain": "microsoft.com", "hl": "en"})
    r.raise_for_status()
    return html_to_text((r.json().get("data") or {}).get("jobDescription"))
