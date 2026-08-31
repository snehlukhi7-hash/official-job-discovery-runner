"""Workday public-CXS discovery with exact-detail validation."""

from __future__ import annotations

from datetime import datetime
from urllib.parse import urlparse

from ..freshness import classify_workday_detail
from ..geography import is_verified_us_location
from ..models import Source


class WorkdayAdapter:
    def __init__(self, transport):
        self.transport = transport
        self.metrics = {}

    @staticmethod
    def _parts(source: Source) -> tuple[str, str, str, str]:
        parsed = urlparse(source.careers_url)
        if parsed.scheme != "https" or ".myworkdayjobs.com" not in parsed.netloc:
            raise ValueError("careers_url must be an HTTPS Workday site")
        tenant = parsed.netloc.split(".", 1)[0]
        path = [part for part in parsed.path.split("/") if part]
        if path and len(path[0]) in {2, 5}:
            path = path[1:]
        site = path[0] if path else "jobs"
        listing = f"https://{parsed.netloc}/wday/cxs/{tenant}/{site}/jobs"
        return parsed.netloc, tenant, site, listing

    async def discover(self, source: Source, fetched_at: datetime) -> list[dict]:
        host, tenant, site, listing_url = self._parts(source)
        listing = await self.transport.json(
            "POST",
            listing_url,
            {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""},
        )
        items = listing.get("jobPostings", [])
        self.metrics = {
            "listing_count": len(items),
            "detail_checked": 0,
            "accepted": 0,
            "identity_rejected": 0,
            "freshness_rejected": 0,
            "geography_rejected": 0,
            "malformed_rejected": 0,
        }
        rows: list[dict] = []
        for item in items:
            external_path = str(item.get("externalPath") or "").strip()
            req_id = str(item.get("jobReqId") or item.get("id") or "").strip()
            if not external_path or not req_id or "/job/" not in external_path:
                self.metrics["malformed_rejected"] += 1
                continue
            tail = external_path.split("/job/", 1)[1].strip("/")
            evidence_url = f"https://{host}/wday/cxs/{tenant}/{site}/job/{tail}"
            detail_payload = await self.transport.json("GET", evidence_url)
            self.metrics["detail_checked"] += 1
            detail = detail_payload.get("jobPostingInfo") or detail_payload
            detail_req = str(
                detail.get("jobReqId") or detail.get("jobRequisitionId") or ""
            ).strip()
            if detail_req and detail_req.casefold() != req_id.casefold():
                self.metrics["identity_rejected"] += 1
                continue
            posted_on = str(detail.get("postedOn") or "").strip()
            start_date = str(detail.get("startDate") or "").strip()
            freshness = classify_workday_detail(posted_on, start_date, fetched_at)
            location = str(detail.get("location") or item.get("locationsText") or "").strip()
            description = str(
                detail.get("jobDescription") or detail.get("description") or ""
            ).strip()
            if freshness.status != "VERIFIED":
                self.metrics["freshness_rejected"] += 1
                continue
            if not is_verified_us_location(location):
                self.metrics["geography_rejected"] += 1
                continue
            official_path = external_path if external_path.startswith("/") else "/" + external_path
            rows.append(
                {
                    "company": source.company,
                    "title": str(item.get("title") or detail.get("title") or "").strip(),
                    "req_id": req_id,
                    "official_url": f"https://{host}/{site}{official_path}",
                    "ats": "workday",
                    "location": location,
                    "country": "US",
                    "employment_type": str(
                        detail.get("timeType") or detail.get("timeTypeLabel") or ""
                    ).strip() or None,
                    "salary_text": str(detail.get("salary") or "").strip() or None,
                    "description": description,
                    "posted_on": posted_on,
                    "start_date": start_date,
                    "fetched_at": fetched_at.isoformat().replace("+00:00", "Z"),
                    "freshness_evidence_scope": "EXACT_REQUISITION",
                    "evidence_url": evidence_url,
                    "dedupe_key": f"{source.company.casefold()}:{req_id.casefold()}",
                }
            )
            self.metrics["accepted"] += 1
        return rows
