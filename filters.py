"""Decide whether a posting fits a 0-1 year software engineer in India.

Stage 1 (cheap, title + location) runs on every new posting.
Stage 2 (experience in the description) runs only on postings that pass stage 1.
All word lists live in config.yaml under `filters`, so they can be tuned without code changes.
"""
import re
from functools import lru_cache

YEARS = r"(?:years?|yrs?)"
N = r"(\d{1,2})"
# Each pattern captures the *minimum* years a phrase asks for.
EXPERIENCE_PATTERNS = [re.compile(p, re.I) for p in (
    rf"{N}\s*\+?\s*(?:-|–|—|to)\s*\d{{1,2}}\s*\+?\s*{YEARS}",            # 2-4 years, 2 to 4 yrs
    rf"{N}\s*{YEARS}\s*(?:-|–|to)\s*\d{{1,2}}\s*{YEARS}",                # 5 years to 13 years
    rf"{N}\s*(?:\+|plus)\s*{YEARS}",                                      # 3+ years
    rf"(?:minimum|min\.?|at\s+least|over|more\s+than)\s*(?:of\s+)?{N}\s*\+?\s*{YEARS}(?:\s+of)?\s+(?:\w+\s+){{0,3}}?(?:experience|exp)",
    rf"{N}\s*(?:or\s+more|and\s+above)\s*{YEARS}",                        # 3 or more years
    rf"{N}\s*{YEARS}(?:\s+of)?\s+(?:\w+\s+){{0,4}}?(?:experience|exp\b)",  # 3 years of professional experience
    rf"\bexp(?:erience)?\s*[:\-]?\s*{N}\s*\+?\s*{YEARS}",                 # Exp: 3 years
)]
MAX_SENSIBLE = 12  # ignore "25+ years of history" etc.


def min_years_required(text: str) -> int | None:
    """Smallest number of years any experience phrase asks for, or None if none stated.
    Taking the minimum is deliberately lenient: we would rather show a borderline job than miss one."""
    found = []
    for pat in EXPERIENCE_PATTERNS:
        for m in pat.finditer(text or ""):
            n = int(m.group(1))
            if n <= MAX_SENSIBLE:
                found.append(n)
    return min(found) if found else None


@lru_cache(maxsize=None)
def _rx(words: tuple) -> re.Pattern:
    return re.compile("|".join(f"(?:{w})" for w in words), re.I)


def check_title_location(title: str, location: str, cfg: dict) -> str | None:
    """Return None if the job passes, else a short reason it was rejected."""
    if not _rx(tuple(cfg["locations"])).search(location or ""):
        return "location"
    m = _rx(tuple(cfg["title_exclude"])).search(title)
    if m:
        return f"title has '{m.group(0).strip()}'"
    if not _rx(tuple(cfg["title_include"])).search(title):
        return "not a software role"
    years = min_years_required(title)
    if years is not None and years > cfg["max_years"]:
        return f"title asks {years}+ yrs"
    return None


def check_experience(description: str, cfg: dict) -> str | None:
    years = min_years_required(description)
    if years is not None and years > cfg["max_years"]:
        return f"needs {years}+ yrs"
    return None
