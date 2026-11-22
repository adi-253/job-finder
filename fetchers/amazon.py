"""amazon.jobs search JSON, filtered to India and the software-development category, newest first."""
from http_utils import TIMEOUT, html_to_text
from models import Job


def fetch(c, s):
    jobs = []
    for p in range(c.get("pages", 2)):
        params = [("country", "IND"), ("result_limit", 100), ("offset", p * 100), ("sort", "recent")]
        params += [("category[]", cat) for cat in c.get("categories", ["software-development"])]
        r = s.get("https://www.amazon.jobs/en/search.json", params=params, timeout=TIMEOUT)
        r.raise_for_status()
        data = r.json()
        for j in data.get("jobs", []):
            jobs.append(Job(
                company=c["name"],
                id=str(j.get("id_icims") or j.get("id")),
                title=j.get("title", "").strip(),
                location=j.get("normalized_location") or j.get("location", ""),
                url="https://www.amazon.jobs" + j.get("job_path", ""),
                posted=j.get("posted_date", ""),
                # only the *basic* qualifications: "preferred" often lists more years than needed
                description=html_to_text(j.get("basic_qualifications")),
            ))
        if (p + 1) * 100 >= data.get("hits", 0):
            break
    return jobs
