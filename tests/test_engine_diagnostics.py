import json

from discovery_runner.engine import discover_sync


def test_zero_row_run_returns_safe_source_diagnostics_without_artifact(tmp_path):
    sources = tmp_path / "sources.json"
    artifact = tmp_path / "jobs.jsonl.gz"
    sources.write_text(
        json.dumps(
            [
                {
                    "company": "Diagnostic Example",
                    "ats": "unsupported",
                    "careers_url": "https://example.com/jobs",
                }
            ]
        ),
        encoding="utf-8",
    )

    summary = discover_sync(sources, artifact)

    assert summary["status"] == "BLOCKED_NO_READY_ARTIFACT"
    assert summary["artifact_total"] == 0
    assert summary["source_errors"] == [
        {"company": "Diagnostic Example", "error": "UNSUPPORTED_ATS"}
    ]
    assert summary["source_metrics"] == []
    assert not artifact.exists()
