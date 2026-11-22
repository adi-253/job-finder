"""Greenhouse public job board API: one call returns every open job."""
from http_utils import TIMEOUT, html_to_text
from models import Job

API = "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"


def fetch(c, s):
    r = s.get(API.format(slug=c["slug"]), timeout=TIMEOUT)
    r.raise_for_status()
    return [
        Job(
            company=c["name"],
            id=str(j["id"]),
            title=j.get("title", "").strip(),
            location=(j.get("location") or {}).get("name", ""),
            url=j.get("absolute_url", ""),
            posted=j.get("first_published") or j.get("updated_at") or "",
        )
        for j in r.json().get("jobs", [])
    ]


def describe(c, s, job):
    r = s.get(f"{API.format(slug=c['slug'])}/{job.id}", timeout=TIMEOUT)
    r.raise_for_status()
    return html_to_text(r.json().get("content"))
