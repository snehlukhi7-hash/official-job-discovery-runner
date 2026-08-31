"""Fail-closed U.S. geography checks for public official listings."""

from __future__ import annotations

import re


_US_POSITIVE = re.compile(
    r"\b(united states(?: of america)?|u\.s\.a\.?|usa)\b|"
    r"(?:,|\s)\s*(?:AL|AK|AZ|AR|CA|CO|CT|DE|FL|GA|HI|ID|IL|IN|IA|KS|KY|LA|"
    r"ME|MD|MA|MI|MN|MS|MO|MT|NE|NV|NH|NJ|NM|NY|NC|ND|OH|OK|OR|PA|RI|SC|SD|"
    r"TN|TX|UT|VT|VA|WA|WV|WI|WY|DC)(?:\b|,)",
    re.IGNORECASE,
)
_FOREIGN = re.compile(
    r"\b(india|canada|colombia|germany|spain|portugal|france|united kingdom|"
    r"australia|argentina|united arab emirates|uae|chennai|calgary|bogot[aá])\b",
    re.IGNORECASE,
)


def is_verified_us_location(location: str) -> bool:
    """Return true only for positive U.S. evidence without foreign collision."""
    value = (location or "").strip()
    if not value or _FOREIGN.search(value):
        return False
    return bool(_US_POSITIVE.search(value))

