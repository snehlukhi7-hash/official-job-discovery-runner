"""Public discovery source definitions."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Source:
    company: str
    ats: str
    careers_url: str

