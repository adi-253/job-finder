"""SmartRecruiters public postings API, filtered to India server-side."""
from http_utils import TIMEOUT, html_to_text
from models import Job

API = "https://api.smartrecruiters.com/v1/companies/{slug}/postings"


def fetch(c, s, pages=3):
    jobs = []
    for p in range(pages):
        r = s.get(API.format(slug=c["slug"]), params={"country": "in", "limit": 100, "offset": p * 100}, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for j in data.get("content", []):
            loc = j.get("location") or {}
            jobs.append(Job(
                company=c["name"],
                id=str(j["id"]),
                title=j.get("name", "").strip(),
                location=", ".join(filter(None, [loc.get("city"), loc.get("region"), "India"])),
                url=f"https://jobs.smartrecruiters.com/{c['slug']}/{j['id']}",
                posted=j.get("releasedDate", ""),
            ))
        if (p + 1) * 100 >= data.get("totalFound", 0):
            break
    return jobs


def describe(c, s, job):
    r = s.get(f"{API.format(slug=c['slug'])}/{job.id}", timeout=TIMEOUT)
    r.raise_for_status()
    sections = ((r.json().get("jobAd") or {}).get("sections")) or {}
    return "\n".join(html_to_text((v or {}).get("text")) for v in sections.values())
