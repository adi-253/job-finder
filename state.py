"""Persisted state: every posting ID seen so far (matched or not) and per-company health.

{
  "seen":    {"Stripe:8172510": "2026-11-22", ...},   # uid -> date last seen in a listing
  "sources": {"Stripe": {"seeded": true, "failures": 0}, ...}
}
"""
import json
from datetime import date, timedelta
from pathlib import Path

FORGET_AFTER_DAYS = 30  # drop IDs not listed for this long (the job was taken down)


def load(path: Path) -> dict:
    if path.exists():
        data = json.loads(path.read_text())
    else:
        data = {}
    data.setdefault("seen", {})
    data.setdefault("sources", {})
    return data


def save(state: dict, path: Path) -> None:
    cutoff = (date.today() - timedelta(days=FORGET_AFTER_DAYS)).isoformat()
    state["seen"] = {k: v for k, v in state["seen"].items() if v >= cutoff}
    path.write_text(json.dumps(state, separators=(",", ":"), sort_keys=True))
