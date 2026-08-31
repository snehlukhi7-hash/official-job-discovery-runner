import asyncio
from datetime import datetime, timezone

from discovery_runner.adapters.workday import WorkdayAdapter
from discovery_runner.models import Source


class FakeTransport:
    def __init__(self, listing, details):
        self.listing = listing
        self.details = details
        self.calls = []

    async def json(self, method, url, payload=None):
        self.calls.append((method, url, payload))
        return self.listing if method == "POST" else self.details[url]


def test_workday_adapter_uses_exact_detail_and_keeps_only_verified_us():
    source = Source(
        company="Example Health",
        ats="workday",
        careers_url="https://example.wd1.myworkdayjobs.com/en-US/jobs",
    )
    listing = {
        "jobPostings": [
            {"title": "Data Analyst", "externalPath": "/job/New-York/REQ-1", "jobReqId": "REQ-1"},
            {"title": "Foreign Analyst", "externalPath": "/job/Chennai/REQ-2", "jobReqId": "REQ-2"},
        ],
        "total": 2,
    }
    base = "https://example.wd1.myworkdayjobs.com/wday/cxs/example/jobs/job"
    details = {
        f"{base}/New-York/REQ-1": {
            "jobPostingInfo": {
                "jobReqId": "REQ-1",
                "postedOn": "Posted Today",
                "startDate": "2026-08-31",
                "location": "New York, NY, United States",
                "jobDescription": "Analyze operational data.",
                "timeType": "Full time",
            }
        },
        f"{base}/Chennai/REQ-2": {
            "jobPostingInfo": {
                "jobReqId": "REQ-2",
                "postedOn": "Posted Today",
                "startDate": "2026-08-31",
                "location": "Chennai, India",
                "jobDescription": "Analyze data.",
            }
        },
    }
    transport = FakeTransport(listing, details)
    adapter = WorkdayAdapter(transport)

    rows = asyncio.run(
        adapter.discover(source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc))
    )

    assert [row["req_id"] for row in rows] == ["REQ-1"]
    assert rows[0]["evidence_url"] == f"{base}/New-York/REQ-1"
    assert transport.calls[0][0] == "POST"
    assert [call[0] for call in transport.calls[1:]] == ["GET", "GET"]


def test_workday_adapter_rejects_list_detail_identity_mismatch():
    source = Source("Example", "workday", "https://example.wd1.myworkdayjobs.com/jobs")
    listing = {"jobPostings": [{"title": "Analyst", "externalPath": "/job/REQ-1", "jobReqId": "REQ-1"}]}
    detail_url = "https://example.wd1.myworkdayjobs.com/wday/cxs/example/jobs/job/REQ-1"
    details = {detail_url: {"jobPostingInfo": {"jobReqId": "REQ-OTHER", "postedOn": "Posted Today", "startDate": "2026-08-31", "location": "New York, NY, United States", "jobDescription": "Data"}}}

    rows = asyncio.run(WorkdayAdapter(FakeTransport(listing, details)).discover(source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc)))
    assert rows == []

