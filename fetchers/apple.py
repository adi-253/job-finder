"""jobs.apple.com. Search pages embed their results as JSON (__staticRouterHydrationData)."""
import json
import re

from http_utils import TIMEOUT, html_to_text
from models import Job

HYDRATION = re.compile(r'__staticRouterHydrationData = JSON\.parse\((".*?")\);', re.S)


def _hydration(page_html):
    m = HYDRATION.search(page_html)
    if not m:
        raise RuntimeError("Apple page layout changed: hydration data not found")
    return json.loads(json.loads(m.group(1)))


def fetch(c, s):
    jobs = []
    for page in range(1, c.get("pages", 3) + 1):
        r = s.get("https://jobs.apple.com/en-in/search", timeout=TIMEOUT, params={
            "search": c.get("query", "software engineer"), "sort": "newest",
            "location": "india-INDC", "page": page,
        })
        r.raise_for_status()
        search = _hydration(r.text)["loaderData"]["search"]
        rows = search.get("searchResults") or []
        for j in rows:
            if (j.get("team") or {}).get("teamName") == "Apple Retail":
                continue
            locs = [l.get("name", "") for l in j.get("locations", [])]
            jobs.append(Job(
                company=c["name"],
                id=str(j.get("positionId") or j["id"]),
                title=j.get("postingTitle", "").strip(),
                location=" / ".join(locs) + " (India)",
                url=f"https://jobs.apple.com/en-in/details/{j.get('positionId')}/{j.get('transformedPostingTitle', '')}",
                posted=j.get("postDateInGMT", ""),
                description=j.get("jobSummary", ""),
            ))
        if not rows or page * 20 >= (search.get("totalRecords") or 0):
            break
    return jobs


def describe(c, s, job):
    r = s.get(job.url, timeout=TIMEOUT)
    r.raise_for_status()
    texts = []

    def walk(o):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and re.search(r"qualif|description|summary", k, re.I):
                    texts.append(html_to_text(v))
                else:
                    walk(v)
        elif isinstance(o, list):
            for v in o:
                walk(v)

    walk(_hydration(r.text).get("loaderData", {}))
    return "\n".join(texts) or job.description
