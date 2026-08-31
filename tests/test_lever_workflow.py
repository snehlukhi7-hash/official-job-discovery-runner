import json
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_lever_now_workflow_is_public_fail_closed_and_persistent():
    text = (ROOT / ".github/workflows/lever-now.yml").read_text(encoding="utf-8")
    assert "sources/lever_sources.json" in text
    assert "discovery-runner final-qa" in text
    assert text.index("discovery-runner final-qa") < text.index("Persist Lever READY payload")
    assert "control/lever-latest/jobs.jsonl.gz" in text
    assert "BLOCKED_NO_READY_ARTIFACT" in text
    assert text.index("set +e") < text.index("discovery-runner run-batch") < text.index("set -e")


def test_lever_sources_are_official_and_nontrivial():
    sources = json.loads((ROOT / "sources/lever_sources.json").read_text(encoding="utf-8"))
    assert len(sources) >= 20
    assert all(item["ats"] == "lever" for item in sources)
    assert all(item["careers_url"].startswith("https://jobs.lever.co/") for item in sources)
