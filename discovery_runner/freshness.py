"""Strict freshness classification for exact official ATS records."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo


ET = ZoneInfo("America/New_York")


@dataclass(frozen=True, slots=True)
class FreshnessResult:
    status: str
    reason: str


def classify_workday_detail(
    posted_on: str, start_date: str, fetched_at: datetime
) -> FreshnessResult:
    """Accept only live exact Workday `Posted Today` with valid date support."""
    posted = " ".join((posted_on or "").strip().lower().split())
    if not posted:
        return FreshnessResult("UNVERIFIED", "POSTED_ON_MISSING")
    if posted in {"posted yesterday", "posted 1 day ago", "1 day ago"}:
        return FreshnessResult("REJECTED", "NOT_POSTED_TODAY")
    if posted != "posted today":
        return FreshnessResult("UNVERIFIED", "POSTED_ON_UNRECOGNIZED")

    try:
        supporting = datetime.strptime(start_date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return FreshnessResult("UNVERIFIED", "SUPPORT_DATE_INVALID")

    today_et = fetched_at.astimezone(ET).date()
    if supporting in {today_et, today_et - timedelta(days=1)}:
        return FreshnessResult("VERIFIED", "LIVE_EXACT_POSTED_TODAY")
    return FreshnessResult("CONTRADICTION", "POSTED_TODAY_DATE_CONTRADICTION")

