"""Atlassian careers listing endpoint: every open job in one call, with descriptions."""
from http_utils import TIMEOUT, html_to_text
from models import Job


def fetch(c, s):
    r = s.get("https://www.atlassian.com/endpoint/careers/listings", timeout=TIMEOUT)
    r.raise_for_status()
    return [
        Job(
            company=c["name"],
            id=str(j["id"]),
            title=j.get("title", "").strip(),
            location=" / ".join(j.get("locations", [])),
            url=f"https://www.atlassian.com/company/careers/details/{j['id']}",
            posted=(j.get("portalJobPost") or {}).get("updatedDate", ""),
            description=html_to_text(" ".join(j.get(k) or "" for k in ("responsibilities", "qualifications"))),
        )
        for j in r.json()
    ]
