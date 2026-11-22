"""Job finder: collect every new posting from each company, filter for 0-1 yr SWE roles in India,
and alert on Telegram.

    python main.py              # normal run (what the GitHub Action does)
    python main.py --dry-run    # fetch + filter + print, no alerts, state not saved
    python main.py --all        # treat every listed job as new: shows all *currently open* matches (implies --dry-run)
    python main.py --only Google,Stripe -v   # test specific companies, print every verdict
"""
import argparse
import os
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import yaml

import notify
import state as st
from fetchers import SOURCES
from filters import check_experience, check_title_location
from http_utils import make_session

ROOT = Path(__file__).parent
FAIL_ALERT_AFTER = 8   # consecutive failed runs (~2 hours) before warning on Telegram; Workday is often briefly rate-limited
MAX_DESCRIBE = 80      # cap on description fetches per run
# GitHub Actions logs of a public repo are public: there, print only counts, never job titles.
PRIVATE_LOGS = not os.environ.get("GITHUB_ACTIONS")


def fetch_company(c):
    t = time.time()
    try:
        return c, SOURCES[c["source"]].fetch(c, make_session()), None, time.time() - t
    except Exception as e:
        return c, None, f"{type(e).__name__}: {e}"[:300], time.time() - t


def run_split(items, fn, workers, queue_of):
    """Run fn over items in parallel. Items with the same queue_of(item) key run one by one:
    Workday rate-limits per data center (wd1, wd5, ...), so each data center gets one queue."""
    queues, free = {}, []
    for x in items:
        q = queue_of(x)
        (queues.setdefault(q, []) if q else free).append(x)
    with ThreadPoolExecutor(workers) as ex:
        queued = [ex.submit(lambda xs=xs: [fn(x) for x in xs]) for xs in queues.values()]
        out = list(ex.map(fn, free))
        for f in queued:
            out += f.result()
        return out


def workday_queue(c):
    return f"workday-{c['dc']}" if c["source"] == "workday" else None


def add_description(item):
    c, job = item
    mod = SOURCES[c["source"]]
    if not job.description and hasattr(mod, "describe"):
        try:
            job.description = mod.describe(c, make_session(), job) or ""
        except Exception as e:  # keep the job; we just can't check its experience
            print(f"  ! could not fetch description for {job.uid}: {e}"[:200])
    return item


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dry-run", action="store_true", help="print results; send nothing; don't save state")
    ap.add_argument("--all", action="store_true", help="evaluate every listed job, not only new ones (implies --dry-run)")
    ap.add_argument("--seed", action="store_true", help="record everything as seen without alerting")
    ap.add_argument("--only", help="comma-separated company names to run")
    ap.add_argument("-v", "--verbose", action="store_true", help="print the verdict for every evaluated job")
    ap.add_argument("--config", default=str(ROOT / "config.yaml"))
    ap.add_argument("--state", default=str(ROOT / "state.json"))
    args = ap.parse_args(argv)
    dry = args.dry_run or args.all

    cfg = yaml.safe_load(Path(args.config).read_text())
    fcfg = cfg["filters"]
    companies = [c for c in cfg["companies"] if not c.get("disabled")]
    if args.only:
        wanted = {n.strip().lower() for n in args.only.split(",")}
        companies = [c for c in companies if c["name"].lower() in wanted]
    for c in companies:
        if c["source"] not in SOURCES:
            sys.exit(f"{c['name']}: unknown source '{c['source']}'")

    state_path = Path(args.state)
    state = st.load(state_path)
    today = date.today().isoformat()
    for c in companies:
        c["cache"] = state["sources"].setdefault(c["name"], {"seeded": False, "failures": 0}).setdefault("cache", {})

    # ---- Stage 0: collect every listed posting, keep the ones not seen before ----
    print(f"Checking {len(companies)} companies…")
    results = run_split(companies, fetch_company, cfg.get("workers", 12), workday_queue)
    candidates, broken, recovered, ok_count = [], [], [], 0
    for c, jobs, err, secs in sorted(results, key=lambda r: r[0]["name"].lower()):
        src = state["sources"][c["name"]]
        if err:
            src["failures"] = src.get("failures", 0) + 1
            print(f"  ✗ {c['name']:<22} failed ({src['failures']}x): {err}")
            if src["failures"] == FAIL_ALERT_AFTER:
                broken.append(c["name"])
            continue
        ok_count += 1
        unique = {}
        for j in jobs:  # some sites list one job once per city
            if j.uid in unique:
                if j.location not in unique[j.uid].location:
                    unique[j.uid].location += f" / {j.location}"
            else:
                unique[j.uid] = j
        jobs = list(unique.values())
        if src.get("failures", 0) >= FAIL_ALERT_AFTER:
            recovered.append(c["name"])
        src["failures"] = 0
        new = [j for j in jobs if j.uid not in state["seen"]]
        for j in jobs:
            state["seen"][j.uid] = today
        first_time = not src.get("seeded")
        src["seeded"] = True
        note = ""
        if args.all:
            new = jobs
        elif first_time or args.seed:
            note = "  (first run: recorded silently)" if first_time else "  (seeded)"
            new = []
        print(f"  ✓ {c['name']:<22} {len(jobs):4} listed {len(new):4} new  {secs:5.1f}s{note}")
        candidates += [(c, j) for j in new]

    # ---- Stage 1: title + location on every new posting ----
    rejected = Counter()
    passed = []
    for c, j in candidates:
        reason = check_title_location(j.title, j.location, fcfg)
        if reason:
            rejected[reason if not reason.startswith("title has") else "senior/other title"] += 1
            if args.verbose and PRIVATE_LOGS:
                print(f"  - {j.company}: {j.title} [{j.location}] → {reason}")
        else:
            passed.append((c, j))

    # ---- Stage 2: experience stated in the description ----
    if len(passed) > MAX_DESCRIBE:
        print(f"  ! {len(passed)} jobs passed stage 1; fetching descriptions for the first {MAX_DESCRIBE} only")
    to_describe = passed[:MAX_DESCRIBE]
    run_split(to_describe, add_description, cfg.get("workers", 12), lambda cj: workday_queue(cj[0]))
    matches = []
    for c, j in passed:
        reason = check_experience(j.description, fcfg)
        if reason:
            rejected[reason] += 1
            if PRIVATE_LOGS:
                print(f"  - {j.company}: {j.title} → {reason}")
        else:
            matches.append(j)
    matches.sort(key=lambda j: (j.company.lower(), j.title.lower()))

    print(f"\n{len(candidates)} new postings → {len(passed)} passed title/location → {len(matches)} matches")
    if rejected:
        print("Rejected: " + ", ".join(f"{k} ×{v}" for k, v in rejected.most_common()))
    if PRIVATE_LOGS:
        for j in matches:
            print(f"  ★ {j.company}: {j.title} [{j.location}] {j.url}")

    if dry:
        print("\n(dry run: nothing sent, state not saved)")
        return 0

    if matches:
        notify.send_jobs(matches)
    if broken:  # one combined message, not one per company
        notify.send_text(f"⚠️ These companies have failed {FAIL_ALERT_AFTER} checks in a row and are being skipped "
                         f"until they recover: {', '.join(broken)}. Usually the site is rate-limiting or changed its layout.")
    if recovered:
        notify.send_text(f"✅ Working again: {', '.join(recovered)}")
    st.save(state, state_path)
    return 0 if ok_count else 1


if __name__ == "__main__":
    sys.exit(main())
