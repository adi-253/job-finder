"""Rippling's own ATS public board API. Lists each job once per location, so we merge them."""
from http_utils import TIMEOUT, html_to_text
from models import Job

API = "https://api.rippling.com/platform/api/ats/v1/board/{slug}/jobs"


def fetch(c, s):
    r = s.get(API.format(slug=c.get("slug", "rippling")), timeout=TIMEOUT)
    r.raise_for_status()
    merged = {}
    for j in r.json():
        loc = (j.get("workLocation") or {}).get("label", "")
        if j["uuid"] in merged:
            if loc and loc not in merged[j["uuid"]].location:
                merged[j["uuid"]].location += f" / {loc}"
            continue
        merged[j["uuid"]] = Job(company=c["name"], id=j["uuid"], title=j.get("name", "").strip(),
                                location=loc, url=j.get("url", ""))
    return list(merged.values())


def describe(c, s, job):
    r = s.get(f"{API.format(slug=c.get('slug', 'rippling'))}/{job.id}", timeout=TIMEOUT)
    r.raise_for_status()
    d = r.json().get("description") or {}
    return "\n".join(html_to_text(v) for k, v in d.items() if k != "company" and isinstance(v, str))
