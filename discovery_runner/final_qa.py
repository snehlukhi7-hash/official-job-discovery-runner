"""Deterministic complete-artifact reconciliation."""

from __future__ import annotations

import gzip
import json
from dataclasses import dataclass
from pathlib import Path

from .export_contract import PublicExportViolation, sanitize_public_job


@dataclass(frozen=True, slots=True)
class FinalQAResult:
    pass_: bool
    artifact_total: int
    unique_keys: int
    reason: str = ""


def run_final_qa(artifact_path: str | Path, summary_path: str | Path) -> FinalQAResult:
    try:
        summary = json.loads(Path(summary_path).read_text(encoding="utf-8"))
        rows = []
        with gzip.open(artifact_path, "rt", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    rows.append(sanitize_public_job(json.loads(line)))
    except (OSError, ValueError, json.JSONDecodeError, PublicExportViolation) as exc:
        return FinalQAResult(False, 0, 0, f"ARTIFACT_INVALID:{exc}")

    keys = [row["dedupe_key"] for row in rows]
    total = len(rows)
    unique = len(set(keys))
    passes = (
        summary.get("status") == "READY_FOR_QUALIFICATION"
        and total > 0
        and total == unique
        and summary.get("artifact_total") == total
    )
    return FinalQAResult(passes, total, unique, "" if passes else "RECONCILIATION_FAILED")

