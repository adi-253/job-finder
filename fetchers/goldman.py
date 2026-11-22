"""Goldman Sachs careers (higher.gs.com). The site's own public GraphQL search; no login needed.

Goldman ranks: Analyst (entry level) → Associate (~3+ yrs) → Vice President. The `levels`
option keeps only the ranks you want (default: Analyst)."""
from models import Job

API = "https://api-higher.gs.com/gateway/api/v1/graphql"
QUERY = """query GetRoles($searchQueryInput: RoleSearchQueryInput!) {
  roleSearch(searchQueryInput: $searchQueryInput) {
    totalCount
    items { roleId corporateTitle jobTitle locations { primary state country city } }
  }
}"""
PAGE = 50


def fetch(c, s):
    levels = {lvl.lower() for lvl in c.get("levels", ["Analyst"])}
    jobs = []
    for p in range(c.get("pages", 6)):
        r = s.post(API, timeout=30, headers={"Origin": "https://higher.gs.com", "Referer": "https://higher.gs.com/"}, json={
            "operationName": "GetRoles", "query": QUERY,
            "variables": {"searchQueryInput": {
                "page": {"pageSize": PAGE, "pageNumber": p}, "filters": [],
                "experiences": ["EARLY_CAREER", "PROFESSIONAL"], "searchTerm": c.get("query", "engineer"),
            }},
        })
        r.raise_for_status()
        body = r.json()
        if body.get("errors"):
            raise RuntimeError(str(body["errors"])[:200])
        data = body["data"]["roleSearch"]
        for j in data["items"]:
            locs = j.get("locations") or []
            if not any((l.get("country") or "") == "India" for l in locs):
                continue  # this search can't filter by country, so do it here
            rank = (j.get("corporateTitle") or "").strip()
            if levels and rank.lower() not in levels:
                continue
            jobs.append(Job(
                company=c["name"],
                id=j["roleId"],
                title=f"{j.get('jobTitle', '').strip()} ({rank})" if rank and rank not in j.get("jobTitle", "") else j.get("jobTitle", "").strip(),
                location=" / ".join(f"{l.get('city') or ''}, {l.get('country')}".strip(", ") for l in locs),
                url=f"https://higher.gs.com/roles/{j['roleId']}",
            ))
        if (p + 1) * PAGE >= data.get("totalCount", 0):
            break
    return jobs
