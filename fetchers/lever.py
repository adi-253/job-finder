"""Lever public postings API: one call returns every open job, with descriptions."""
from datetime import datetime, timezone

from http_utils import TIMEOUT
from models import Job


def fetch(c, s):
    r = s.get(f"https://api.lever.co/v0/postings/{c['slug']}?mode=json", timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json():
        cat = j.get("categories") or {}
        locs = cat.get("allLocations") or [cat.get("location", "")]
        desc = "\n".join(
            [j.get("descriptionPlain", "")]
            + [f"{l.get('text', '')}\n{l.get('content', '')}" for l in j.get("lists", [])]
            + [j.get("additionalPlain", "")]
        )
        created = j.get("createdAt")
        jobs.append(Job(
            company=c["name"],
            id=j["id"],
            title=j.get("text", "").strip(),
            location=" / ".join(filter(None, locs)) + (f" ({j['country']})" if j.get("country") else ""),
            url=j.get("hostedUrl", ""),
            posted=datetime.fromtimestamp(created / 1000, timezone.utc).isoformat() if created else "",
            description=desc,
        ))
    return jobs
