import gzip
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from discovery_runner.freshness import classify_workday_detail
from discovery_runner.geography import is_verified_us_location
from discovery_runner.public_artifacts import (
    PublicArtifactViolation,
    write_public_artifact,
)


def public_job(req_id="REQ-1"):
    return {
        "company": "Example Health",
        "title": "Data Analyst",
        "req_id": req_id,
        "official_url": f"https://example.com/jobs/{req_id}",
        "ats": "workday",
        "location": "New York, NY, United States",
        "country": "US",
        "employment_type": "Full time",
        "salary_text": None,
        "description": "Analyze public operational data.",
        "posted_on": "Posted Today",
        "start_date": "2026-08-31",
        "fetched_at": "2026-08-31T12:00:00Z",
        "freshness_evidence_scope": "EXACT_REQUISITION",
        "evidence_url": f"https://example.com/wday/cxs/e/jobs/job/{req_id}",
        "dedupe_key": f"example-health:{req_id}",
    }


def test_public_artifact_round_trip_and_summary(tmp_path):
    output = tmp_path / "jobs.jsonl.gz"
    summary = write_public_artifact([public_job()], output)

    assert summary.total == summary.unique_keys == 1
    with gzip.open(output, "rt", encoding="utf-8") as handle:
        assert json.loads(handle.readline())["req_id"] == "REQ-1"


def test_public_artifact_rejects_duplicate_keys_without_writing(tmp_path):
    output = tmp_path / "jobs.jsonl.gz"
    with pytest.raises(PublicArtifactViolation, match="duplicate"):
        write_public_artifact([public_job(), public_job()], output)
    assert not output.exists()


@pytest.mark.parametrize(
    ("posted_on", "start_date", "status"),
    [
        ("Posted Today", "2026-08-31", "VERIFIED"),
        ("Posted Today", "2026-08-30", "VERIFIED"),
        ("Posted Today", "2026-08-29", "CONTRADICTION"),
        ("Posted Yesterday", "2026-08-30", "REJECTED"),
        ("1 Day Ago", "2026-08-30", "REJECTED"),
        ("", "2026-08-31", "UNVERIFIED"),
    ],
)
def test_workday_freshness_is_fail_closed(posted_on, start_date, status):
    now = datetime(2026, 8, 31, 16, tzinfo=timezone.utc)
    assert classify_workday_detail(posted_on, start_date, now).status == status


@pytest.mark.parametrize(
    ("location", "expected"),
    [
        ("New York, NY, United States", True),
        ("Remote - United States", True),
        ("Chennai, India", False),
        ("Calgary, Canada", False),
        ("Bogota, Colombia", False),
        ("Remote", False),
    ],
)
def test_us_geography_requires_positive_evidence(location, expected):
    assert is_verified_us_location(location) is expected


def test_discovery_package_contains_no_private_capability_terms():
    forbidden = ("tsenta", "gmail", "resume_profile", "submit_application", "apply_to_job")
    violations = []
    package = Path(__file__).parents[1] / "discovery_runner"
    for path in package.rglob("*.py"):
        text = path.read_text(encoding="utf-8").lower()
        for term in forbidden:
            if term in text:
                violations.append(f"{path.name}:{term}")
    assert violations == []
