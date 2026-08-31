import json

from discovery_runner.final_qa import run_final_qa
from discovery_runner.public_artifacts import write_public_artifact
from test_public_engine import public_job


def test_final_qa_reconciles_complete_artifact(tmp_path):
    artifact = tmp_path / "jobs.jsonl.gz"
    summary = tmp_path / "summary.json"
    write_public_artifact([public_job("REQ-1"), public_job("REQ-2")], artifact)
    summary.write_text(json.dumps({"status": "READY_FOR_QUALIFICATION", "artifact_total": 2}), encoding="utf-8")

    result = run_final_qa(artifact, summary)
    assert result.pass_ is True
    assert result.artifact_total == result.unique_keys == 2


def test_final_qa_fails_if_summary_count_disagrees(tmp_path):
    artifact = tmp_path / "jobs.jsonl.gz"
    summary = tmp_path / "summary.json"
    write_public_artifact([public_job()], artifact)
    summary.write_text(json.dumps({"status": "READY_FOR_QUALIFICATION", "artifact_total": 2}), encoding="utf-8")
    assert run_final_qa(artifact, summary).pass_ is False

