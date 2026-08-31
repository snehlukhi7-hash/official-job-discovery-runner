from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_ashby_now_workflow_is_public_fail_closed_and_persistent():
    text = (ROOT / ".github/workflows/ashby-now.yml").read_text(encoding="utf-8")
    assert "sources/ashby_sources.json" in text
    assert "discovery-runner final-qa" in text
    assert text.index("discovery-runner final-qa") < text.index("Persist Ashby READY payload")
    assert "control/ashby-latest/jobs.jsonl.gz" in text
    assert "control/ashby-latest/summary.json" in text
    assert "retention-days: 1" in text
    forbidden = ("ts" + "enta", "gm" + "ail", "res" + "ume", "sub" + "mit")
    assert [term for term in forbidden if term in text.lower()] == []
