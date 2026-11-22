"""Ashby public job board API: one call returns every open job, with descriptions."""
from http_utils import TIMEOUT
from models import Job


def fetch(c, s):
    r = s.get(f"https://api.ashbyhq.com/posting-api/job-board/{c['slug']}", timeout=TIMEOUT)
    r.raise_for_status()
    jobs = []
    for j in r.json().get("jobs", []):
        if j.get("isListed") is False:
            continue
        locs = [j.get("location", "")] + [l.get("location", "") for l in j.get("secondaryLocations") or []]
        country = (((j.get("address") or {}).get("postalAddress")) or {}).get("addressCountry", "")
        jobs.append(Job(
            company=c["name"],
            id=j["id"],
            title=j.get("title", "").strip(),
            location=" / ".join(filter(None, locs)) + (f" ({country})" if country else ""),
            url=j.get("jobUrl", ""),
            posted=j.get("publishedAt", ""),
            description=j.get("descriptionPlain", ""),
        ))
    return jobs
