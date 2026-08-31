"""Fail-closed export boundary for public job artifacts."""

from __future__ import annotations

from datetime import date, datetime
from typing import Any, Mapping
from urllib.parse import urlparse


PUBLIC_JOB_FIELDS = (
    "company",
    "title",
    "req_id",
    "official_url",
    "ats",
    "location",
    "country",
    "employment_type",
    "salary_text",
    "description",
    "posted_on",
    "start_date",
    "fetched_at",
    "freshness_evidence_scope",
    "evidence_url",
    "dedupe_key",
)


class PublicExportViolation(ValueError):
    """Raised when a record cannot safely cross the public boundary."""


_REQUIRED_STRINGS = (
    "company",
    "title",
    "req_id",
    "ats",
    "location",
    "description",
    "fetched_at",
    "dedupe_key",
)


def _is_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value)
    return parsed.scheme == "https" and bool(parsed.netloc)


def _validate(sanitized: Mapping[str, Any]) -> list[str]:
    errors: list[str] = []
    for field in _REQUIRED_STRINGS:
        value = sanitized[field]
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    if sanitized["country"] != "US":
        errors.append("country must be US")
    for field in ("official_url", "evidence_url"):
        if not _is_https_url(sanitized[field]):
            errors.append(f"{field} must be an HTTPS URL")
    for field in (
        "employment_type",
        "salary_text",
        "posted_on",
        "freshness_evidence_scope",
    ):
        if sanitized[field] is not None and not isinstance(sanitized[field], str):
            errors.append(f"{field} must be a string or null")
    if sanitized["start_date"] is not None:
        try:
            date.fromisoformat(sanitized["start_date"])
        except (TypeError, ValueError):
            errors.append("start_date must be an ISO date or null")
    try:
        datetime.fromisoformat(sanitized["fetched_at"].replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        errors.append("fetched_at must be an ISO date-time")
    return errors


def sanitize_public_job(job: Mapping[str, Any]) -> dict[str, Any]:
    """Return a validated allowlisted record, rejecting unknown fields."""
    extras = sorted(set(job) - set(PUBLIC_JOB_FIELDS))
    if extras:
        raise PublicExportViolation(
            "non-public field(s) rejected: " + ", ".join(extras)
        )

    sanitized = {field: job.get(field) for field in PUBLIC_JOB_FIELDS}
    errors = _validate(sanitized)
    if errors:
        raise PublicExportViolation("; ".join(errors))
    return sanitized
