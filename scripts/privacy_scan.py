"""Fail closed when a public tree contains secrets or private capabilities."""

from __future__ import annotations

import re
import sys
from pathlib import Path


TEXT_SUFFIXES = {".py", ".yml", ".yaml", ".json", ".toml", ".md", ".txt", ".csv"}
SKIP_PARTS = {".git", "__pycache__", ".pytest_cache"}
FORBIDDEN_PATH_PARTS = {
    "adaptive" + "_pro",
    "candidate" + "s",
    "re" + "sumes",
    "tracker" + "_data",
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"),
    re.compile(r"(?i)(?:api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]\s*['\"][^'\"]{8,}"),
)
CAPABILITY_TERMS = (
    "ts" + "enta",
    "gm" + "ail",
    "resume" + "_profile",
    "submit" + "_application",
    "apply" + "_to_job",
)


def scan(root: Path) -> list[str]:
    violations = []
    for path in root.rglob("*"):
        if not path.is_file() or any(part in SKIP_PARTS for part in path.parts):
            continue
        relative = path.relative_to(root)
        lowered_parts = {part.casefold() for part in relative.parts}
        if lowered_parts & FORBIDDEN_PATH_PARTS:
            violations.append(f"forbidden path: {relative}")
        if path.suffix.casefold() not in TEXT_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if relative.as_posix() != "scripts/privacy_scan.py" and "tests" not in relative.parts:
            lowered = text.casefold()
            for term in CAPABILITY_TERMS:
                if term in lowered:
                    violations.append(f"forbidden capability term in {relative}: {term}")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                violations.append(f"credential pattern in {relative}")
    return violations


def main(argv=None) -> int:
    root = Path((argv or sys.argv[1:] or ["."])[0]).resolve()
    violations = scan(root)
    if violations:
        print("\n".join(violations))
        return 1
    print(f"privacy scan passed: {root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

