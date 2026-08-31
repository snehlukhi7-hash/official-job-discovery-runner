import asyncio
from datetime import datetime, timezone

from discovery_runner.adapters.greenhouse import GreenhouseAdapter
from discovery_runner.models import Source


class FakeTransport:
    def __init__(self, payload):
        self.payload = payload
        self.calls = []

    async def json(self, method, url, payload=None):
        self.calls.append((method, url, payload))
        return self.payload


def test_greenhouse_accepts_fresh_exact_us_job():
    transport = FakeTransport({"jobs": [{
        "id": 123,
        "requisition_id": "REQ-123",
        "title": "Financial Analyst",
        "absolute_url": "https://job-boards.greenhouse.io/example/jobs/123",
        "location": {"name": "New York, NY"},
        "updated_at": "2026-08-31T10:00:00Z",
        "content": "Analyze financial controls and reporting.",
    }]})
    source = Source(company="Example", ats="greenhouse", careers_url="https://job-boards.greenhouse.io/example")

    rows = asyncio.run(GreenhouseAdapter(transport).discover(
        source, datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
    ))

    assert len(rows) == 1
    assert rows[0]["req_id"] == "REQ-123"
    assert rows[0]["freshness_evidence_scope"] == "EXACT_REQUISITION"
    assert rows[0]["evidence_url"] == "https://boards-api.greenhouse.io/v1/boards/example/jobs/123"
    assert transport.calls == [("GET", "https://boards-api.greenhouse.io/v1/boards/example/jobs?content=true", None)]


def test_greenhouse_rejects_stale_and_unverified_remote_jobs():
    transport = FakeTransport({"jobs": [
        {"id": 1, "title": "Analyst", "absolute_url": "https://job-boards.greenhouse.io/example/jobs/1", "location": {"name": "New York, NY"}, "updated_at": "2026-08-29T10:00:00Z", "content": "Stale"},
        {"id": 2, "title": "Analyst", "absolute_url": "https://job-boards.greenhouse.io/example/jobs/2", "location": {"name": "Remote"}, "updated_at": "2026-08-31T10:00:00Z", "content": "Unknown geography"},
    ]})
    source = Source(company="Example", ats="greenhouse", careers_url="https://job-boards.greenhouse.io/example")

    adapter = GreenhouseAdapter(transport)
    assert asyncio.run(adapter.discover(source, datetime(2026, 8, 31, 12, tzinfo=timezone.utc))) == []
    assert adapter.metrics["freshness_rejected"] == 1
    assert adapter.metrics["geography_rejected"] == 1
