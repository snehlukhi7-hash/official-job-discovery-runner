"""Lever public job-board discovery with exact-posting revalidation."""

from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from urllib.parse import urlparse

from ..geography import is_verified_us_location
from ..models import Source


class LeverAdapter:
    def __init__(self, transport):
        self.transport = transport
        self.metrics = {}

    @staticmethod
    def _board_id(source: Source) -> str:
        parsed = urlparse(source.careers_url)
        if parsed.scheme != "https" or parsed.netloc != "jobs.lever.co":
            raise ValueError("careers_url must be an HTTPS Lever job board")
        board_id = parsed.path.strip("/").split("/", 1)[0]
        if not board_id:
            raise ValueError("Lever board id is missing")
        return board_id

    @staticmethod
    def _created_at(value: object) -> datetime | None:
        try:
            milliseconds = int(value)
            return datetime.fromtimestamp(milliseconds / 1000, tz=timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return None

    @staticmethod
    def _plain_description(item: dict) -> str:
        parts = [
            str(item.get("descriptionPlain") or ""),
            str(item.get("additionalPlain") or ""),
        ]
        for block in item.get("lists") or []:
            if isinstance(block, dict):
                parts.extend((str(block.get("text") or ""), str(block.get("content") or "")))
        text = html.unescape(" ".join(parts))
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    @staticmethod
    def _salary_text(item: dict) -> str | None:
        value = item.get("salaryRange")
        if not isinstance(value, dict):
            return None
        minimum, maximum = value.get("min"), value.get("max")
        if minimum is None and maximum is None:
            return None
        currency = str(value.get("currency") or "").strip()
        interval = str(value.get("interval") or "").strip()
        return " ".join(part for part in (str(minimum), "-", str(maximum), currency, interval) if part).strip()

    async def discover(self, source: Source, fetched_at: datetime) -> list[dict]:
        board_id = self._board_id(source)
        listing_url = f"https://api.lever.co/v0/postings/{board_id}?mode=json"
        payload = await self.transport.json("GET", listing_url)
        if not isinstance(payload, list):
            raise ValueError("Lever postings must be a list")
        self.metrics = {
            "listing_count": len(payload), "detail_checked": 0, "accepted": 0,
            "identity_rejected": 0, "freshness_rejected": 0,
            "geography_rejected": 0, "malformed_rejected": 0,
        }
        now = fetched_at.astimezone(timezone.utc)
        rows = []
        for listing in payload:
            if not isinstance(listing, dict):
                self.metrics["malformed_rejected"] += 1
                continue
            job_id = str(listing.get("id") or "").strip()
            created = self._created_at(listing.get("createdAt"))
            categories = listing.get("categories") or {}
            location = str(categories.get("location") if isinstance(categories, dict) else "").strip()
            if created is None or not (0 <= (now - created).total_seconds() <= 86400):
                self.metrics["freshness_rejected"] += 1
                continue
            if not is_verified_us_location(location):
                self.metrics["geography_rejected"] += 1
                continue
            if not job_id:
                self.metrics["malformed_rejected"] += 1
                continue
            evidence_url = f"https://api.lever.co/v0/postings/{board_id}/{job_id}"
            detail = await self.transport.json("GET", evidence_url)
            self.metrics["detail_checked"] += 1
            if not isinstance(detail, dict) or str(detail.get("id") or "").strip() != job_id:
                self.metrics["identity_rejected"] += 1
                continue
            official_url = str(detail.get("hostedUrl") or "").strip()
            description = self._plain_description(detail)
            if not official_url.startswith(f"https://jobs.lever.co/{board_id}/") or not description:
                self.metrics["malformed_rejected"] += 1
                continue
            detail_created = self._created_at(detail.get("createdAt"))
            if detail_created is None or detail_created != created:
                self.metrics["identity_rejected"] += 1
                continue
            detail_categories = detail.get("categories") or {}
            employment = (
                str(detail_categories.get("commitment") or "").strip()
                if isinstance(detail_categories, dict) else ""
            )
            rows.append({
                "company": source.company,
                "title": str(detail.get("text") or "").strip(),
                "req_id": job_id,
                "official_url": official_url,
                "ats": "lever",
                "location": location,
                "country": "US",
                "employment_type": employment or None,
                "salary_text": self._salary_text(detail),
                "description": description,
                "posted_on": created.isoformat().replace("+00:00", "Z"),
                "start_date": created.date().isoformat(),
                "fetched_at": now.isoformat().replace("+00:00", "Z"),
                "freshness_evidence_scope": "EXACT_REQUISITION",
                "evidence_url": evidence_url,
                "dedupe_key": f"{source.company.casefold()}:lever:{job_id.casefold()}",
            })
            self.metrics["accepted"] += 1
        return rows
