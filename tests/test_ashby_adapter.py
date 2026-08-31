import asyncio
from datetime import datetime, timezone

from discovery_runner.adapters.ashby import AshbyAdapter
from discovery_runner.models import Source


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def json(self, method, url, payload=None):
        self.calls.append((method, url, payload))
        return self.payload


def test_ashby_accepts_fresh_exact_us_job():
    transport = FakeTransport(
        {
            "jobs": [
                {
                    "id": "job-123",
                    "title": "Business Systems Analyst",
                    "jobUrl": "https://jobs.ashbyhq.com/example/job-123",
                    "location": "Remote - United States",
                    "employmentType": "FullTime",
                    "publishedAt": "2026-08-31T00:00:00Z",
                    "descriptionPlain": "Analyze business systems and data.",
                }
            ]
        }
    )
    source = Source(
        company="Example",
        ats="ashby",
        careers_url="https://jobs.ashbyhq.com/example",
    )

    rows = asyncio.run(
        AshbyAdapter(transport).discover(
            source, datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
        )
    )

    assert len(rows) == 1
    assert rows[0]["req_id"] == "job-123"
    assert rows[0]["posted_on"] == "2026-08-31T00:00:00Z"
    assert rows[0]["freshness_evidence_scope"] == "EXACT_REQUISITION"
    assert rows[0]["evidence_url"] == rows[0]["official_url"]
    assert transport.calls == [
        ("GET", "https://api.ashbyhq.com/posting-api/job-board/example", None)
    ]


def test_ashby_rejects_stale_and_unverified_remote_jobs():
    transport = FakeTransport(
        {
            "jobs": [
                {
                    "id": "stale",
                    "title": "Data Analyst",
                    "jobUrl": "https://jobs.ashbyhq.com/example/stale",
                    "location": "United States",
                    "publishedAt": "2026-08-29T00:00:00Z",
                    "descriptionPlain": "Stale.",
                },
                {
                    "id": "remote",
                    "title": "Data Analyst",
                    "jobUrl": "https://jobs.ashbyhq.com/example/remote",
                    "location": "Remote",
                    "publishedAt": "2026-08-31T08:00:00Z",
                    "descriptionPlain": "Unverified geography.",
                },
            ]
        }
    )
    source = Source(
        company="Example",
        ats="ashby",
        careers_url="https://jobs.ashbyhq.com/example",
    )

    adapter = AshbyAdapter(transport)
    rows = asyncio.run(
        adapter.discover(
            source, datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
        )
    )

    assert rows == []
    assert adapter.metrics["freshness_rejected"] == 1
    assert adapter.metrics["geography_rejected"] == 1
