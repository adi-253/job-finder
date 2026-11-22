import sys
from pathlib import Path

import pytest
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from filters import check_experience, check_title_location, min_years_required  # noqa: E402

CFG = yaml.safe_load((Path(__file__).resolve().parents[1] / "config.yaml").read_text())["filters"]
BLR = "Bengaluru, Karnataka, India"


@pytest.mark.parametrize("title", [
    "Software Engineer I",
    "Software Engineer I – Backend",
    "Software Development Engineer",
    "SDE 1",
    "Software Engineer",
    "Software Engineering IC2",
    "Junior Software Development Engineer in Test, Sales Engineering",
    "Associate Software Engineer",
    "Member of Technical Staff",
    "Backend Developer",
    "Full Stack Engineer",
    "Software Engineer, New Grad",
    "Software Engineer | Java/Golang/Python | 2 to 4 years | Bangalore",
])
def test_accepts_junior_titles(title):
    assert check_title_location(title, BLR, CFG) is None


@pytest.mark.parametrize("title", [
    "Senior SDE",
    "Sr. Software Engineer",
    "Software Dev Engineer II, Amazon Freight",
    "Software Engineer 2: AI Builder",
    "Staff Software Engineer",
    "Principal Software Engineer IC5",
    "Engineering Manager",
    "Lead Software Engineer - Java Backend",
    "Software Engineering Intern",
    "Senior Member Technical Staff",
    "LMTS - Lead AI/ML Engineer",
    "Account Executive",
    "Sales Engineer",
    "Solutions Engineer",
    "ASIC Design Engineer",
    "Senior Verification Engineer",
    "Embedded Software Engineer - C, Linux, Networking (5+ yrs)",
    "Datacenter Technician",
    "Mgr, Software Engrg Mgmt",
    "Cloud Engineer, AVP",
    "Technical Account Engineer I",
])
def test_rejects_other_titles(title):
    assert check_title_location(title, BLR, CFG) is not None


@pytest.mark.parametrize("loc", ["Bengaluru", "IN, TS, Hyderabad", "Pune, India", "Gurugram", "India, Multiple Locations",
                                 "Remote - India - Remote", "Noida, Uttar Pradesh"])
def test_india_locations(loc):
    assert check_title_location("Software Engineer", loc, CFG) is None


@pytest.mark.parametrize("loc", ["Seattle, WA", "Dublin, Ireland", "Remote - US", "Singapore", "Indianapolis, IN"])
def test_non_india_locations(loc):
    assert check_title_location("Software Engineer", loc, CFG) == "location"


@pytest.mark.parametrize("text,years", [
    ("You have 3+ years of experience building backend systems", 3),
    ("0-2 years of experience in Java", 0),
    ("Minimum of 5 years of relevant experience", 5),
    ("at least 1 year of experience with Python", 1),
    ("2 to 4 years of software development experience", 2),
    ("Bachelor's degree or equivalent practical experience.", None),
    ("Experience: 4 years in distributed systems", 4),
    ("5+ years in backend. 1+ years with Kubernetes", 1),   # lenient: smallest stated requirement
    ("Founded over 25 years ago, we have 25+ years of history", None),
])
def test_min_years(text, years):
    assert min_years_required(text) == years


def test_experience_filter():
    assert check_experience("Requires 3+ years of experience", CFG) is not None
    assert check_experience("Requires 2+ years of experience", CFG) is None
    assert check_experience("", CFG) is None
