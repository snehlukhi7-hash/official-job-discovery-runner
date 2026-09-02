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
    assert adapter.metrics == {
        "listing_count": 2,
        "detail_checked": 2,
        "accepted": 1,
        "identity_rejected": 0,
        "freshness_rejected": 0,
        "geography_rejected": 1,
        "malformed_rejected": 0,
    }


def test_workday_adapter_rejects_list_detail_identity_mismatch():
    source = Source("Example", "workday", "https://example.wd1.myworkdayjobs.com/jobs")
    listing = {"jobPostings": [{"title": "Analyst", "externalPath": "/job/REQ-1", "jobReqId": "REQ-1"}]}
    detail_url = "https://example.wd1.myworkdayjobs.com/wday/cxs/example/jobs/job/REQ-1"
    details = {detail_url: {"jobPostingInfo": {"jobReqId": "REQ-OTHER", "postedOn": "Posted Today", "startDate": "2026-08-31", "location": "New York, NY, United States", "jobDescription": "Data"}}}

    rows = asyncio.run(WorkdayAdapter(FakeTransport(listing, details)).discover(source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc)))
    assert rows == []


def test_structured_foreign_country_overrides_ambiguous_state_code():
    source = Source("Example", "workday", "https://example.wd1.myworkdayjobs.com/jobs")
    listing = {
        "jobPostings": [
            {
                "title": "Operations Manager",
                "externalPath": "/job/East-Bunbury-WA/REQ-1",
                "jobReqId": "REQ-1",
            }
        ],
        "total": 1,
    }
    detail_url = (
        "https://example.wd1.myworkdayjobs.com/wday/cxs/example/jobs/job/"
        "East-Bunbury-WA/REQ-1"
    )
    details = {
        detail_url: {
            "jobPostingInfo": {
                "jobReqId": "REQ-1",
                "postedOn": "Posted Today",
                "startDate": "2026-08-31",
                "location": "East Bunbury, WA",
                "jobDescription": "Operations",
                "jobRequisitionLocation": {
                    "country": {"alpha2Code": "AU"}
                },
            }
        }
    }

    adapter = WorkdayAdapter(FakeTransport(listing, details))
    rows = asyncio.run(
        adapter.discover(source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc))
    )

    assert rows == []
    assert adapter.metrics["geography_rejected"] == 1


def test_workday_adapter_extracts_req_id_when_listing_omits_id_fields():
    source = Source("Example", "workday", "https://example.wd1.myworkdayjobs.com/jobs")
    listing = {
        "jobPostings": [
            {
                "title": "Analyst",
                "externalPath": "/job/New-York/Analyst_JR0286635",
                "bulletFields": ["Job ID: JR0286635"],
            }
        ]
    }
    detail_url = "https://example.wd1.myworkdayjobs.com/wday/cxs/example/jobs/job/New-York/Analyst_JR0286635"
    details = {
        detail_url: {
            "jobPostingInfo": {
                "jobReqId": "JR0286635",
                "postedOn": "Posted Today",
                "startDate": "2026-08-31",
                "location": "New York, NY, United States",
                "jobDescription": "Data",
            }
        }
    }

    rows = asyncio.run(
        WorkdayAdapter(FakeTransport(listing, details)).discover(
            source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc)
        )
    )
    assert [row["req_id"] for row in rows] == ["JR0286635"]


def test_workday_adapter_paginates_listing_to_source_exhaustion():
    source = Source("Example", "workday", "https://example.wd1.myworkdayjobs.com/jobs")
    pages = {
        0: {
            "total": 21,
            "jobPostings": [
                {
                    "title": f"Old role {number}",
                    "externalPath": f"/job/Old/REQ-{number}",
                    "jobReqId": f"REQ-{number}",
                }
                for number in range(1, 21)
            ],
        },
        20: {
            "total": 21,
            "jobPostings": [
                {
                    "title": "Fresh analyst",
                    "externalPath": "/job/New-York/REQ-21",
                    "jobReqId": "REQ-21",
                }
            ],
        },
    }
    detail_base = "https://example.wd1.myworkdayjobs.com/wday/cxs/example/jobs/job"

    class PagingTransport:
        def __init__(self):
            self.calls = []

        async def json(self, method, url, payload=None):
            self.calls.append((method, url, payload))
            if method == "POST":
                return pages[payload["offset"]]
            req_id = url.rsplit("/", 1)[-1]
            fresh = req_id == "REQ-21"
            return {
                "jobPostingInfo": {
                    "jobReqId": req_id,
                    "postedOn": "Posted Today" if fresh else "Posted Yesterday",
                    "startDate": "2026-08-31",
                    "location": "New York, NY, United States",
                    "jobDescription": "Data",
                    "timeType": "Full time",
                }
            }

    transport = PagingTransport()
    adapter = WorkdayAdapter(transport)
    rows = asyncio.run(
        adapter.discover(source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc))
    )

    assert [row["req_id"] for row in rows] == ["REQ-21"]
    assert [call[2]["offset"] for call in transport.calls if call[0] == "POST"] == [0, 20]
    assert adapter.metrics["listing_count"] == 21
    assert adapter.metrics["detail_checked"] == 21


def test_workday_adapter_rejects_url_tail_identity_mismatch():
    source = Source("CarMax", "workday", "https://carmax.wd1.myworkdayjobs.com/jobs")
    listing = {
        "jobPostings": [
            {
                "title": "Auto Parts Associate",
                "externalPath": "/job/Remote/Auto-Parts-Associate_JR-124632",
                "jobReqId": "JE-124632",
            }
        ],
        "total": 1,
    }
    detail_url = (
        "https://carmax.wd1.myworkdayjobs.com/wday/cxs/carmax/jobs/job/"
        "Remote/Auto-Parts-Associate_JR-124632"
    )
    details = {
        detail_url: {
            "jobPostingInfo": {
                "jobReqId": "JE-124632",
                "postedOn": "Posted Today",
                "startDate": "2026-08-31",
                "location": "Remote, United States",
                "jobDescription": "Analyze parts operations data.",
                "timeType": "Full time",
            }
        }
    }
    adapter = WorkdayAdapter(FakeTransport(listing, details))
    rows = asyncio.run(
        adapter.discover(source, datetime(2026, 8, 31, 16, tzinfo=timezone.utc))
    )
    assert rows == []
    assert adapter.metrics["identity_rejected"] == 1
