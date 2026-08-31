# Official Job Discovery Runner

This public project collects only official, public job-listing data and produces a one-day artifact for a separate private qualification process.

It is intentionally narrow:

- official ATS discovery only
- exact requisition identity checks
- strict Workday `Posted Today` validation using exact live CXS detail
- current or previous America/New_York date as supporting date-only evidence
- positive United States geography evidence
- allowlisted 16-field gzip JSONL output
- no credentials or personal data

The workflow uses standard public GitHub-hosted runners, validates the entire artifact, and checks for an existing same-window READY artifact before Python setup or installation.

## Local verification

```bash
python -m pip install -e '.[test]'
python -m pytest -q
python scripts/privacy_scan.py .
python -m compileall -q discovery_runner
```

## Run discovery

```bash
discovery-runner run-batch \
  --sources sources/public_sources.json \
  --artifact output/jobs.jsonl.gz \
  --summary-file output/summary.json
discovery-runner final-qa \
  --artifact output/jobs.jsonl.gz \
  --summary-file output/summary.json
```
