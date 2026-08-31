import pytest

from discovery_runner.export_contract import (
    PUBLIC_JOB_FIELDS,
    PublicExportViolation,
    sanitize_public_job,
)


def valid_job():
    return {
        "company": "Example Corp",
        "title": "Data Analyst",
        "req_id": "REQ-123",
        "official_url": "https://example.com/jobs/REQ-123",
        "ats": "workday",
        "location": "New York, NY",
        "country": "US",
        "employment_type": "Full time",
        "salary_text": "$100,000-$120,000",
        "description": "Analyze operational data.",
        "posted_on": "Posted Today",
        "start_date": "2026-08-31",
        "fetched_at": "2026-08-31T12:00:00Z",
        "freshness_evidence_scope": "EXACT_REQUISITION",
        "evidence_url": "https://example.com/wday/cxs/example/jobs/job/REQ-123",
        "dedupe_key": "example-corp:REQ-123",
    }


def test_sanitizer_emits_only_public_allowlisted_fields():
    result = sanitize_public_job(valid_job())
    assert tuple(result) == PUBLIC_JOB_FIELDS


@pytest.mark.parametrize(
    "private_field",
    [
        "candidate_name",
        "candidate_email",
        "resume_text",
        "resume_profile_id",
        "tsenta_application_id",
        "tracker_row",
        "authorization_answer",
        "api_key",
    ],
)
def test_sanitizer_fails_closed_on_any_non_allowlisted_field(private_field):
    row = valid_job()
    row[private_field] = "must-not-export"

    with pytest.raises(PublicExportViolation, match=private_field):
        sanitize_public_job(row)


def test_sanitizer_rejects_missing_required_identity():
    row = valid_job()
    del row["req_id"]

    with pytest.raises(PublicExportViolation):
        sanitize_public_job(row)
