"""Greenhouse public job-board discovery using exact official ATS rows."""

from __future__ import annotations

from datetime import datetime, timezone
from urllib.parse import urlparse

from ..geography import is_verified_us_location
from ..models import Source


class GreenhouseAdapter:
    def __init__(self, transport):
        self.transport = transport
        self.metrics = {}

    @staticmethod
    def _board_id(source: Source) -> str:
        parsed = urlparse(source.careers_url)
        if parsed.scheme != "https" or parsed.netloc not in {"boards.greenhouse.io", "job-boards.greenhouse.io"}:
            raise ValueError("careers_url must be an HTTPS Greenhouse job board")
        board_id = parsed.path.strip("/").split("/", 1)[0]
        if not board_id:
            raise ValueError("Greenhouse board id is missing")
        return board_id

    @staticmethod
    def _timestamp(value: object) -> datetime | None:
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
        endpoint = f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs?content=true"
        payload = await self.transport.json("GET", endpoint)
        items = payload.get("jobs", []) if isinstance(payload, dict) else []
        if not isinstance(items, list):
            raise ValueError("Greenhouse jobs must be a list")
        self.metrics = {
            "listing_count": len(items), "detail_checked": len(items), "accepted": 0,
            "identity_rejected": 0, "freshness_rejected": 0,
            "geography_rejected": 0, "malformed_rejected": 0,
        }
        now = fetched_at.astimezone(timezone.utc)
        rows = []
        for item in items:
            job_id = str(item.get("id") or "").strip()
            req_id = str(item.get("requisition_id") or job_id).strip()
            official_url = str(item.get("absolute_url") or "").strip()
            location_obj = item.get("location") or {}
            location = str(location_obj.get("name") if isinstance(location_obj, dict) else location_obj).strip()
            updated_raw = str(item.get("updated_at") or "").strip()
            updated = self._timestamp(updated_raw)
            description = str(item.get("content") or "").strip()
            if not job_id or not req_id or not official_url.startswith("https://") or not description:
                self.metrics["malformed_rejected"] += 1
                continue
            if updated is None or not (0 <= (now - updated).total_seconds() <= 86400):
                self.metrics["freshness_rejected"] += 1
                continue
            if not is_verified_us_location(location):
                self.metrics["geography_rejected"] += 1
                continue
            rows.append({
                "company": source.company,
                "title": str(item.get("title") or "").strip(),
                "req_id": req_id,
                "official_url": official_url,
                "ats": "greenhouse",
                "location": location,
                "country": "US",
                "employment_type": None,
                "salary_text": None,
                "description": description,
                "posted_on": updated_raw,
                "start_date": updated.date().isoformat(),
                "fetched_at": now.isoformat().replace("+00:00", "Z"),
                "freshness_evidence_scope": "EXACT_REQUISITION",
                "evidence_url": f"https://boards-api.greenhouse.io/v1/boards/{board_id}/jobs/{job_id}",
                "dedupe_key": f"{source.company.casefold()}:{req_id.casefold()}",
            })
            self.metrics["accepted"] += 1
        return rows
