"""Command-line entrypoint exposing discovery and final QA only."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from .engine import discover_sync
from .final_qa import run_final_qa


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="discovery-runner", description="Official public job discovery")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run-batch", help="collect and validate official public jobs")
    run.add_argument("--sources", required=True)
    run.add_argument("--artifact", required=True)
    run.add_argument("--summary-file", required=True)
    qa = commands.add_parser("final-qa", help="reconcile a complete public artifact")
    qa.add_argument("--artifact", required=True)
    qa.add_argument("--summary-file", required=True)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run-batch":
        summary = discover_sync(args.sources, args.artifact)
        Path(args.summary_file).write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(summary, indent=2))
        return 0 if summary.get("status") == "READY_FOR_QUALIFICATION" else 1
    result = run_final_qa(args.artifact, args.summary_file)
    print(json.dumps(asdict(result), indent=2))
    return 0 if result.pass_ else 1


if __name__ == "__main__":
    raise SystemExit(main())
