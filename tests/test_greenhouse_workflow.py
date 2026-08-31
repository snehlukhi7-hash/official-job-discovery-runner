import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_greenhouse_now_workflow_is_public_fail_closed_and_persistent():
    text = (ROOT / ".github/workflows/greenhouse-now.yml").read_text(encoding="utf-8")
    assert "sources/greenhouse_sources.json" in text
    assert "discovery-runner final-qa" in text
    assert text.index("discovery-runner final-qa") < text.index("Persist Greenhouse READY payload")
    assert "control/greenhouse-latest/jobs.jsonl.gz" in text
    forbidden = ("ts" + "enta", "gm" + "ail", "res" + "ume", "sub" + "mit")
    assert [term for term in forbidden if term in text.lower()] == []


def test_greenhouse_sources_are_official_and_nontrivial():
    sources = json.loads((ROOT / "sources/greenhouse_sources.json").read_text(encoding="utf-8"))
    assert len(sources) >= 20
    assert all(item["ats"] == "greenhouse" for item in sources)
    assert all(item["careers_url"].startswith("https://job-boards.greenhouse.io/") for item in sources)
