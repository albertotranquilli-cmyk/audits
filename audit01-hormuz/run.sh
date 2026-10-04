#!/usr/bin/env bash
# AUDIT #1 - one-command reproduction.
#   bash run.sh           downloads the PortWatch inputs if data/raw is empty, then rebuilds everything
#   bash run.sh --fresh   always re-downloads (PortWatch revises past data weekly, Tuesdays 9:00 ET)
# Options (environment): AUDIT_END=2026-09-25 (default, window used in the thread) or AUDIT_END=auto;
#                        AUDIT_DOI="https://doi.org/..." (printed in the chart footer).
set -euo pipefail
H="$(cd "$(dirname "$0")" && pwd)"; cd "$H"
FRESH="${1:-}"
if [ ! -x .venv/bin/python ]; then
  python3 -m venv .venv && .venv/bin/pip install --quiet -r requirements.txt
fi
PY=.venv/bin/python
rm -rf out && mkdir -p out data/raw
echo "== 1. data (IMF PortWatch public API; polite, read-only)"
$PY scripts/get_data.py $FRESH
echo "== 2. records vs the AUDIT #1 manifest"
$PY scripts/check_records.py
echo "== 3. analysis"
$PY scripts/analysis.py | tee out/facts.txt
echo "== 4. chart"
$PY scripts/make_chart.py
(cd out && sha256sum * > SHA256SUMS)
echo "== output sha256 (out/SHA256SUMS)"; cat out/SHA256SUMS
echo "run finished $(date -u +%Y-%m-%dT%H:%M:%SZ)"
