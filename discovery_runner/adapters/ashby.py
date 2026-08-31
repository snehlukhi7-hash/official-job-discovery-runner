"""Ashby public job-board discovery with exact timestamp validation."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from ..geography import is_verified_us_location
from ..models import Source


class AshbyAdapter:
    def __init__(self, transport):
        self.transport = transport
        self.metrics = {}

    @staticmethod
    def _board_id(source: Source) -> str:
        parsed = urlparse(source.careers_url)
        if parsed.scheme != "https" or parsed.netloc != "jobs.ashbyhq.com":
            raise ValueError("careers_url must be an HTTPS Ashby job board")
        board_id = parsed.path.strip("/").split("/", 1)[0]
        if not board_id:
            raise ValueError("Ashby board id is missing")
        return board_id

    @staticmethod
    def _published_at(value: object) -> datetime | None:
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)

    async def discover(self, source: Source, fetched_at: datetime) -> list[dict]:
        board_id = self._board_id(source)
        endpoint = f"https://api.ashbyhq.com/posting-api/job-board/{board_id}"
        payload = await self.transport.json("GET", endpoint)
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            raise ValueError("Ashby jobs must be a list")
        self.metrics = {
            "listing_count": len(items),
            "detail_checked": len(items),
            "accepted": 0,
            "identity_rejected": 0,
            "freshness_rejected": 0,
            "geography_rejected": 0,
            "malformed_rejected": 0,
        }
        now = fetched_at.astimezone(timezone.utc)
        rows = []
        for item in items:
            official_url = str(item.get("jobUrl") or item.get("applyUrl") or "").strip()
            req_id = str(
                item.get("id")
                or item.get("jobId")
                or official_url.rstrip("/").rsplit("/", 1)[-1]
            ).strip()
            published_raw = str(item.get("publishedAt") or "").strip()
            published = self._published_at(published_raw)
            location = str(item.get("location") or "").strip()
            description = str(
                item.get("descriptionPlain") or item.get("descriptionHtml") or ""
            ).strip()
            if (
                not official_url.startswith("https://jobs.ashbyhq.com/")
                or not req_id
                or not description
            ):
                self.metrics["malformed_rejected"] += 1
                continue
            if published is None or not (0 <= (now - published).total_seconds() <= 86400):
                self.metrics["freshness_rejected"] += 1
                continue
            if not is_verified_us_location(location):
                self.metrics["geography_rejected"] += 1
                continue
            rows.append(
                {
                    "company": source.company,
                    "title": str(item.get("title") or "").strip(),
                    "req_id": req_id,
                    "official_url": official_url,
                    "ats": "ashby",
                    "location": location,
                    "country": "US",
                    "employment_type": str(item.get("employmentType") or "").strip() or None,
                    "salary_text": str(item.get("compensation") or "").strip() or None,
                    "description": description,
                    "posted_on": published_raw,
                    "start_date": published.date().isoformat(),
                    "fetched_at": now.isoformat().replace("+00:00", "Z"),
                    "freshness_evidence_scope": "EXACT_REQUISITION",
                    "evidence_url": official_url,
                    "dedupe_key": f"{source.company.casefold()}:{req_id.casefold()}",
                }
            )
            self.metrics["accepted"] += 1
        return rows
