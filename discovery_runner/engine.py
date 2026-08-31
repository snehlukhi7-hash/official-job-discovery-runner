"""Discovery-only batch orchestration."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from .adapters.workday import WorkdayAdapter
from .models import Source
from .public_artifacts import write_public_artifact
from .transport import JsonTransport


async def discover(sources_path: str | Path, artifact_path: str | Path) -> dict:
    definitions = json.loads(Path(sources_path).read_text(encoding="utf-8"))
    sources = [Source(**item) for item in definitions]
    transport = JsonTransport()
    fetched_at = datetime.now(timezone.utc)
    rows = []
    errors = []
    source_metrics = []
    for source in sources:
        if source.ats.casefold() != "workday":
            errors.append({"company": source.company, "error": "UNSUPPORTED_ATS"})
            continue
        try:
            adapter = WorkdayAdapter(transport)
            rows.extend(await adapter.discover(source, fetched_at))
            source_metrics.append({"company": source.company, **adapter.metrics})
        except Exception as exc:
            errors.append({"company": source.company, "error": type(exc).__name__})
    if not rows:
        return {
            "status": "BLOCKED_NO_READY_ARTIFACT",
            "artifact_total": 0,
            "unique_keys": 0,
            "sources_total": len(sources),
            "source_errors": errors,
            "source_metrics": source_metrics,
        }
    summary = write_public_artifact(rows, artifact_path)
    return {
        "status": "READY_FOR_QUALIFICATION",
        "artifact_total": summary.total,
        "unique_keys": summary.unique_keys,
        "sources_total": len(sources),
        "source_errors": errors,
        "source_metrics": source_metrics,
    }


def discover_sync(sources_path: str | Path, artifact_path: str | Path) -> dict:
    return asyncio.run(discover(sources_path, artifact_path))
