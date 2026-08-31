from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_harvest_workflow_dedupes_before_expensive_setup():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8")
    assert "group: public-harvest-${{ github.sha }}" in text
    dedupe = text.index("id: dedupe")
    assert dedupe < text.index("actions/setup-python@")
    assert dedupe < text.index("pip install")
    assert "item.workflow_run?.head_sha === context.sha" in text


def test_harvest_uses_et_timezone_and_one_day_retention():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8")
    assert text.count("timezone: America/New_York") == 9
    assert "retention-days: 1" in text
    assert "ubuntu-latest" in text


def test_workflow_has_no_private_service_or_job_delivery_capability():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8").lower()
    forbidden = ("ts" + "enta", "gm" + "ail", "res" + "ume", "sub" + "mit", "app" + "ly")
    assert [term for term in forbidden if term in text] == []


def test_ready_payload_is_persisted_only_after_discovery_and_upload():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8")
    persist = text.index("name: Persist latest sanitized READY payload")
    assert text.index("name: Discover") < persist
    assert text.index("name: Upload READY artifact") < persist
    assert "cp output/jobs.jsonl.gz control/latest-v2/jobs.jsonl.gz" in text
    assert "cp output/summary.json control/latest-v2/summary.json" in text
    assert "python scripts/privacy_scan.py ." in text[text.index("name: Persist latest sanitized READY payload"):]
    assert "contents: write" in text
