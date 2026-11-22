"""Oracle Recruiting Cloud (Oracle HCM) career sites: Oracle itself, JPMorgan Chase and others.

Public REST endpoint that the career site itself calls. The India location ID is looked up
from the site's location facets the first time and cached between runs (like Workday)."""
from http_utils import TIMEOUT, html_to_text
from models import Job

LIST = "https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
DETAIL = "https://{host}/hcmRestApi/resources/latest/recruitingCEJobRequisitionDetails"


def _get(s, c, url, finder, expand):
    r = s.get(url.format(host=c["host"]), timeout=TIMEOUT, headers={"Accept": "application/json"},
              params={"onlyData": "true", "expand": expand, "finder": finder})
    r.raise_for_status()
    return r.json()["items"][0] if r.json().get("items") else {}


def _india_id(s, c):
    item = _get(s, c, LIST, f"findReqs;siteNumber={c['site']},facetsList=LOCATIONS,limit=1", "locationsFacet")
    for loc in item.get("locationsFacet") or []:
        if (loc.get("Name") or "").strip().lower() == "india":
            return loc["Id"]
    raise RuntimeError("could not find the India location facet")


def fetch(c, s):
    cache = c.get("cache", {})
    loc_id = cache.get("india_id") or _india_id(s, c)
    cache["india_id"] = loc_id
    jobs = []
    for p in range(c.get("pages", 2)):
        item = _get(s, c, LIST, f"findReqs;siteNumber={c['site']},limit=100,offset={p * 100},"
                                f"locationId={loc_id},sortBy=POSTING_DATES_DESC", "requisitionList.secondaryLocations")
        rows = item.get("requisitionList") or []
        for j in rows:
            locs = [j.get("PrimaryLocation", "")] + [l.get("Name", "") for l in j.get("secondaryLocations") or []]
            jobs.append(Job(
                company=c["name"],
                id=str(j["Id"]),
                title=(j.get("Title") or "").strip(),
                location=" / ".join(dict.fromkeys(filter(None, locs))),
                url=f"https://{c.get('public_host', c['host'])}/hcmUI/CandidateExperience/en/sites/{c['site']}/job/{j['Id']}",
                posted=j.get("PostedDate", ""),
            ))
        if len(rows) < 100:
            break
    return jobs


def describe(c, s, job):
    d = _get(s, c, DETAIL, f'ById;Id="{job.id}",siteNumber={c["site"]}', "all")
    return "\n".join(html_to_text(d.get(k)) for k in
                     ("ExternalDescriptionStr", "ExternalQualificationsStr", "ExternalResponsibilitiesStr"))
