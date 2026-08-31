"""Discovery-only batch orchestration."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from .adapters.workday import WorkdayAdapter
from .adapters.ashby import AshbyAdapter
from .models import Source
from .public_artifacts import write_public_artifact
from .transport import JsonTransport


async def discover(sources_path: str | Path, artifact_path: str | Path) -> dict:
    definitions = json.loads(Path(sources_path).read_text(encoding="utf-8"))
    sources = [Source(**item) for item in definitions]
    transport = JsonTransport()
    fetched_at = datetime.now(timezone.utc)
    semaphore = asyncio.Semaphore(8)

    async def discover_source(source: Source):
        adapter_type = source.ats.casefold()
        if adapter_type not in {"workday", "ashby"}:
            return [], {"company": source.company, "error": "UNSUPPORTED_ATS"}, None
        try:
            adapter = (
                WorkdayAdapter(transport)
                if adapter_type == "workday"
                else AshbyAdapter(transport)
            )
            async with semaphore:
                source_rows = await adapter.discover(source, fetched_at)
            return source_rows, None, {"company": source.company, **adapter.metrics}
        except Exception as exc:
            return [], {"company": source.company, "error": type(exc).__name__}, None

    results = await asyncio.gather(*(discover_source(source) for source in sources))
    rows = [row for source_rows, _, _ in results for row in source_rows]
    errors = [error for _, error, _ in results if error is not None]
    source_metrics = [metrics for _, _, metrics in results if metrics is not None]
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
