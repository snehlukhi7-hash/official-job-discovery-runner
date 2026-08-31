import asyncio
from datetime import datetime, timezone

from discovery_runner.adapters.lever import LeverAdapter
from discovery_runner.models import Source


class FakeTransport:
    def __init__(self, listing, details):
        self.listing = listing
        self.details = details
        self.calls = []

    async def json(self, method, url, payload=None):
        self.calls.append((method, url, payload))
        if "/postings/example/" in url:
            return self.details[url.rsplit("/", 1)[-1]]
        return self.listing


def test_lever_accepts_fresh_exact_us_job_after_detail_revalidation():
    item = {
        "id": "job-123",
        "text": "Financial Analyst",
        "hostedUrl": "https://jobs.lever.co/example/job-123",
        "createdAt": 1788156000000,
        "categories": {"location": "New York, NY", "commitment": "Full-time"},
        "descriptionPlain": "Analyze financial controls and reporting.",
    }
    transport = FakeTransport([item], {"job-123": item})
    source = Source(company="Example", ats="lever", careers_url="https://jobs.lever.co/example")

    rows = asyncio.run(LeverAdapter(transport).discover(
        source, datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    ))

    assert len(rows) == 1
    assert rows[0]["req_id"] == "job-123"
    assert rows[0]["freshness_evidence_scope"] == "EXACT_REQUISITION"
    assert rows[0]["evidence_url"] == "https://api.lever.co/v0/postings/example/job-123"
    assert rows[0]["dedupe_key"] == "example:lever:job-123"
    assert transport.calls[-1] == (
        "GET", "https://api.lever.co/v0/postings/example/job-123", None
    )


def test_lever_rejects_stale_and_unverified_remote_jobs_without_detail_calls():
    stale = {
        "id": "old", "text": "Analyst", "hostedUrl": "https://jobs.lever.co/example/old",
        "createdAt": 1787900000000, "categories": {"location": "New York, NY"},
        "descriptionPlain": "Old job",
    }
    remote = {
        "id": "remote", "text": "Analyst", "hostedUrl": "https://jobs.lever.co/example/remote",
        "createdAt": 1788156000000, "categories": {"location": "Remote"},
        "descriptionPlain": "Unknown geography",
    }
    source = Source(company="Example", ats="lever", careers_url="https://jobs.lever.co/example")
    transport = FakeTransport([stale, remote], {})
    adapter = LeverAdapter(transport)

    assert asyncio.run(adapter.discover(
        source, datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    )) == []
    assert adapter.metrics["freshness_rejected"] == 1
    assert adapter.metrics["geography_rejected"] == 1
    assert len(transport.calls) == 1
