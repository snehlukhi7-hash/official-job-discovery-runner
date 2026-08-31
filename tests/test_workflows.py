from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_harvest_workflow_dedupes_before_expensive_setup():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8")
    dedupe = text.index("id: dedupe")
    assert dedupe < text.index("actions/setup-python@")
    assert dedupe < text.index("pip install")


def test_harvest_uses_et_timezone_and_one_day_retention():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8")
    assert text.count("timezone: America/New_York") == 9
    assert "retention-days: 1" in text
    assert "ubuntu-latest" in text


def test_workflow_has_no_private_service_or_job_delivery_capability():
    text = (ROOT / ".github/workflows/harvest.yml").read_text(encoding="utf-8").lower()
    forbidden = ("ts" + "enta", "gm" + "ail", "res" + "ume", "sub" + "mit", "app" + "ly")
    assert [term for term in forbidden if term in text] == []
