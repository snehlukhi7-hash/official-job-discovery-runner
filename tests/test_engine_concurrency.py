import asyncio
import json

from discovery_runner import engine


def test_sources_are_discovered_concurrently_without_losing_rows(tmp_path, monkeypatch):
    sources = tmp_path / "sources.json"
    artifact = tmp_path / "jobs.jsonl.gz"
    sources.write_text(
        json.dumps(
            [
                {
                    "company": f"Example {index}",
                    "ats": "workday",
                    "careers_url": f"https://example{index}.wd1.myworkdayjobs.com/jobs",
                }
                for index in range(3)
            ]
        ),
        encoding="utf-8",
    )
    state = {"active": 0, "max_active": 0}

    class FakeAdapter:
        def __init__(self, transport):
            self.metrics = {}

        async def discover(self, source, fetched_at):
            state["active"] += 1
            state["max_active"] = max(state["max_active"], state["active"])
            await asyncio.sleep(0.02)
            state["active"] -= 1
            req_id = source.company.rsplit(" ", 1)[-1]
            self.metrics = {"accepted": 1}
            return [
                {
                    "company": source.company,
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
                    "start_date": fetched_at.date().isoformat(),
                    "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
                    "freshness_evidence_scope": "EXACT_REQUISITION",
                    "evidence_url": f"https://example.com/wday/cxs/e/jobs/job/{req_id}",
                    "dedupe_key": f"example:{req_id}",
                }
            ]

    monkeypatch.setattr(engine, "WorkdayAdapter", FakeAdapter)

    summary = engine.discover_sync(sources, artifact)

    assert summary["artifact_total"] == 3
    assert state["max_active"] > 1
