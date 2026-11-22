"""jobs.intuit.com (Radancy). Its results endpoint returns an HTML fragment inside JSON, newest first."""
import html
import re

from http_utils import TIMEOUT, html_to_text
from models import Job

BASE = "https://jobs.intuit.com"
ITEM = re.compile(r'<a href="([^"]+)" data-job-id="(\d+)".*?<h2>(.*?)</h2>.*?class="job-location">(.*?)</span>', re.S)


def fetch(c, s):
    r = s.get(f"{BASE}/search-jobs/results", timeout=TIMEOUT, params={
        "ActiveFacetID": 0, "CurrentPage": 1, "RecordsPerPage": 100, "Keywords": c.get("query", "software engineer"),
        "Location": "India", "SortCriteria": 1, "SortDirection": 1, "SearchType": 5, "ResultsType": 0,
        "SearchResultsModuleName": "Search Results", "SearchFiltersModuleName": "Search Filters",
    }, headers={"X-Requested-With": "XMLHttpRequest"})
    r.raise_for_status()
    return [
        Job(company=c["name"], id=jid, title=html.unescape(title).strip(),
            location=html.unescape(loc).strip(), url=BASE + href)
        for href, jid, title, loc in ITEM.findall(r.json().get("results", ""))
    ]


def describe(c, s, job):
    r = s.get(job.url, timeout=TIMEOUT)
    r.raise_for_status()
    page = r.text
    start = page.find('class="job-description pane pane-jd"')
    end = page.find('class="job-description__buttons bottom"', start)
    if start < 0:
        return ""  # layout changed: skip the experience check rather than scan the whole page
    return html_to_text(page[start:end if end > 0 else start + 30000].split(">", 1)[-1])
