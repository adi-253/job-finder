"""Workday career sites (wd*.myworkdayjobs.com), via the JSON API their pages use.

Each tenant names its location filter differently, so we first discover the India
facet from the response, then read the newest pages. With no search text, Workday
lists newest first, so a few pages per run catch every new posting.

Workday rate-limits bursts across all tenants, so main.py runs Workday companies
one after another and this module sleeps between requests.
"""
import re
import time

from http_utils import TIMEOUT, html_to_text
from models import Job

PAGE = 20
DELAY = 1.5
INDIA = re.compile(r"\bindia\b|bengaluru|bangalore|hyderabad|pune|gurugram|gurgaon|noida|chennai|mumbai|delhi", re.I)


def _base(c):
    return f"https://{c['tenant']}.{c['dc']}.myworkdayjobs.com/wday/cxs/{c['tenant']}/{c['site']}"


def _host(c):
    return f"https://{c['tenant']}.{c['dc']}.myworkdayjobs.com"


def _warm_up(s, c):
    """Open the career page once, like a browser, to get Workday's session cookies.
    API calls without them get rate-limited (HTTP 429) much sooner."""
    if s.cookies.get("PLAY_SESSION"):
        return
    try:
        s.get(f"{_host(c)}/en-US/{c['site']}", timeout=TIMEOUT, headers={"Accept": "text/html"})
    except Exception:
        pass  # the API call may still work


def _post(s, c, body):
    _warm_up(s, c)
    time.sleep(DELAY)
    r = s.post(f"{_base(c)}/jobs", json=body, timeout=TIMEOUT, headers={
        "Content-Type": "application/json", "Accept": "application/json",
        "Origin": _host(c), "Referer": f"{_host(c)}/en-US/{c['site']}",
    })
    r.raise_for_status()
    return r.json()


def _flatten(facets):
    for f in facets or []:
        param = f.get("facetParameter")
        for v in f.get("values", []):
            if "facetParameter" in v:  # nested facet group
                yield from _flatten([v])
            elif v.get("id"):
                yield param, v["id"], v.get("descriptor", "")


def india_facet(facets):
    """{param: [ids]} restricting results to India, or None if not found."""
    vals = list(_flatten(facets))
    exact = [(p, i) for p, i, d in vals if d.strip().lower() == "india"]
    if exact:
        p, i = exact[0]
        return {p: [i]}
    by_param = {}
    for p, i, d in vals:
        if "location" in (p or "").lower() and INDIA.search(d):
            by_param.setdefault(p, []).append(i)
    if not by_param:
        return None
    p = max(by_param, key=lambda k: len(by_param[k]))
    return {p: by_param[p]}


def _discover(s, c):
    first = _post(s, c, {"appliedFacets": {}, "limit": 1, "offset": 0, "searchText": ""})
    facet = india_facet(first.get("facets"))
    if facet is None:
        raise RuntimeError("could not find an India location facet")
    return facet


def fetch(c, s):
    # main.py passes a per-company `cache` dict that is saved between runs, so the
    # facet lookup costs one extra request only the first time (or if the site changes).
    cache = c.get("cache", {})
    facet = cache.get("facet") or _discover(s, c)
    jobs = []
    for p in range(c.get("pages", 2)):
        try:
            data = _post(s, c, {"appliedFacets": facet, "limit": PAGE, "offset": p * PAGE, "searchText": ""})
        except Exception:
            if p == 0 and "facet" in cache:  # stale cached facet: rediscover once
                cache.pop("facet")
                return fetch(c, s)
            raise
        cache["facet"] = facet
        for j in data.get("jobPostings", []):
            path = j.get("externalPath", "")
            loc = j.get("locationsText", "")
            jobs.append(Job(
                company=c["name"],
                id=path,
                title=j.get("title", "").strip(),
                # the India facet guarantees an India location, even when Workday says "3 Locations"
                location=loc if INDIA.search(loc) else f"{loc} (India)",
                url=f"{_host(c)}/en-US/{c['site']}{path}",
                posted=j.get("postedOn", ""),
            ))
        if (p + 1) * PAGE >= data.get("total", 0):
            break
    return jobs


def describe(c, s, job):
    _warm_up(s, c)
    time.sleep(DELAY)
    r = s.get(f"{_base(c)}{job.id}", timeout=TIMEOUT, headers={"Accept": "application/json"})
    r.raise_for_status()
    return html_to_text((r.json().get("jobPostingInfo") or {}).get("jobDescription"))
