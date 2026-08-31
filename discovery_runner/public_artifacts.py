"""Atomic public-artifact writer with dedupe and export validation."""

from __future__ import annotations

import gzip
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Any

from .export_contract import PublicExportViolation, sanitize_public_job


class PublicArtifactViolation(ValueError):
    """Raised when an artifact would be incomplete or unsafe."""


@dataclass(frozen=True, slots=True)
class PublicArtifactSummary:
    total: int
    unique_keys: int


def write_public_artifact(
    rows: Iterable[Mapping[str, Any]], path: str | Path
) -> PublicArtifactSummary:
    """Validate the complete batch before atomically publishing a gzip JSONL."""
    try:
        sanitized = [sanitize_public_job(row) for row in rows]
    except PublicExportViolation as exc:
        raise PublicArtifactViolation(str(exc)) from exc
    keys = [str(row["dedupe_key"]) for row in sanitized]
    if len(keys) != len(set(keys)):
        raise PublicArtifactViolation("duplicate dedupe_key")
    if not sanitized:
        raise PublicArtifactViolation("empty artifacts cannot become ready")

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary_name = tempfile.mkstemp(
        prefix=destination.name + ".", suffix=".tmp", dir=destination.parent
    )
    os.close(handle)
    temporary = Path(temporary_name)
    try:
        with gzip.open(temporary, "wt", encoding="utf-8", newline="\n") as stream:
            for row in sanitized:
                stream.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
                stream.write("\n")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return PublicArtifactSummary(total=len(sanitized), unique_keys=len(set(keys)))

