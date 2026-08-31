from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_exact_workday_workflow_reuses_final_qa_before_persistence():
    text = (ROOT / ".github/workflows/exact-workday-now.yml").read_text(encoding="utf-8")
    assert "sources/exact_workday_source.json" in text
    assert "discovery-runner final-qa" in text
    assert text.index("discovery-runner final-qa") < text.index("Persist exact Workday READY payload")
    assert "control/exact-workday-latest/jobs.jsonl.gz" in text
    assert "control/exact-workday-latest/summary.json" in text
    forbidden = ("ts" + "enta", "gm" + "ail", "res" + "ume", "sub" + "mit")
    assert [term for term in forbidden if term in text.lower()] == []
