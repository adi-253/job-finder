"""Google Careers. The results page embeds its data as JSON (AF_initDataCallback 'ds:1').
target_level=EARLY is Google's own entry-level filter."""
import json
import re
from datetime import datetime, timezone

from http_utils import TIMEOUT, html_to_text
from models import Job

URL = "https://www.google.com/about/careers/applications/jobs/results/"
DS1 = re.compile(r"AF_initDataCallback\(\{key: 'ds:1', hash: '\d+', data:(.*?), sideChannel: \{\}\}\);", re.S)


def parse(page_html):
    m = DS1.search(page_html)
    if not m:
        raise RuntimeError("Google page layout changed: ds:1 data block not found")
    data = json.loads(m.group(1))
    return data[0] or [], data[2] or 0


def fetch(c, s):
    jobs = []
    for page in range(1, c.get("pages", 3) + 1):
        params = [("location", "India"), ("sort_by", "date"), ("page", page), ("q", c.get("query", ""))]
        params += [("target_level", lvl) for lvl in c.get("levels", ["EARLY"])]
        r = s.get(URL, params=params, timeout=TIMEOUT)
        r.raise_for_status()
        rows, total = parse(r.text)
        for j in rows:
            locs = [l[0] for l in (j[9] or []) if l]
            ts = (j[12] or [None])[0]
            desc = "\n".join(html_to_text(x[1]) for x in (j[4], j[19]) if isinstance(x, list) and len(x) > 1)
            jobs.append(Job(
                company=c["name"],
                id=j[0],
                title=j[1],
                location=" / ".join(locs),
                url=f"{URL}{j[0]}",
                posted=datetime.fromtimestamp(ts, timezone.utc).isoformat() if ts else "",
                description=desc,
            ))
        if not rows or page * 20 >= total:
            break
    return jobs
