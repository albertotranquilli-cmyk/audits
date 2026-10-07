# AUDIT #1 forensic checks

Machine-readable reproduction and stress tests for AUDIT #1 (IMF PortWatch, Strait of Hormuz). Standard library only;
does not import `scripts/analysis.py`. No PortWatch data is stored in this repository: inputs are downloaded by
`scripts/get_data.py` into `data/raw/` (git-ignored).

## Reproduce from a pinned commit

```
git clone https://github.com/albertotranquilli-cmyk/audits.git && cd audits
git checkout <COMMIT>                         # the commit recorded in results/<date>/manifest.json -> code.git_head
cd audit01-hormuz
python3 scripts/get_data.py --fresh           # ~15 polite requests, >= 6 s apart; writes data/raw + data/provenance.jsonl
python3 forensic/run_forensic.py --raw data/raw --out forensic/out --fetch-docs
python3 -m unittest discover -s forensic/tests -v
```

Optional: `--compare LABEL=DIR` (repeatable) recomputes the key numbers on another downloaded release for the
revision-sensitivity check. `--fetch-docs` makes 2 extra requests (ArcGIS item descriptions) to check the field
definitions; without it that check is `UNKNOWN`. Window end is pinned by `get_data.py` (`AUDIT_END=2026-09-25`).

## Outputs (`--out`)

- `results.json`: every check with `question`, `hypothesis`, `observed`, `status` and `evidence`, plus measurements
  for both windows (see below).
- `manifest.json`: input files (URL, retrieval time UTC from `data/provenance.jsonl`, byte SHA-256, canonical-records
  SHA-256, provenance match). Byte hashes can change between downloads of the same release (serialization); the
  records hash and `revision_sensitivity.*.inputs_fingerprint` identify the data content,
  PortWatch release (`lastEditDate`), code (`git rev-parse HEAD`, dirty flag, SHA-256 of every forensic script),
  dependencies (Python, platform, installed pipeline packages), SHA-256 of outputs.
- `SHA256SUMS`.

## Status semantics

- `PASS`: the stated hypothesis holds on the observed inputs.
- `FAIL`: it does not. In robustness and falsification checks a `FAIL` is a finding, not a crash.
- `UNKNOWN`: not observable with these inputs (e.g. vessel-level duplicates in daily aggregates) or not attempted.

No status claims more than the hypothesis it states. All values are PortWatch model estimates in metric tonnes.

## Checks

| id | what |
|---|---|
| `capacity_field_schema` | summed fields exist as integers in the layer schema (which has no field descriptions) |
| `capacity_field_definition` | ArcGIS item descriptions define them as estimated cargo in metric tons (payload share x DWT); needs `--fetch-docs` |
| `ballast_zeroing_applied_to_series` | always `UNKNOWN`: documented (WP/25/93, 2025 changelog), not observable in aggregates |
| `units_integer_tonnes`, `aggregation_consistency_port105` | non-negative integers; server-side monthly sums equal daily sums |
| `published_numbers_reproduce` | each published thread number vs recomputation, at the published rounding |
| `duplicate_keys`, `duplicate_vessel_events` | duplicate keys / identical rows; vessel-level duplicates are `UNKNOWN` |
| `row_completeness`, `ais_signal_gaps` | missing daily rows; AIS gaps inside rows are `UNKNOWN` |
| `revision_sensitivity` | gap change between complete releases (`--compare`) |
| `denominator_choice` | tonnage ratio vs a unit-free count ratio, each against its pre-crisis maximum |
| `falsify_port_sets`, `falsify_windows` | alternative inside-Gulf port sets; every window start from 2025-03 |
| `negative_control_pre_crisis_windows` | all pre-crisis 7-month windows must have (E-I)/C <= 1 |
| `negative_control_leave_one_port_out` | is port105 the largest absolute contributor? |
| `negative_control_excess_over_own_baseline` | is port105 the most anomalous vs its own 2019-2024 median? (added post hoc) |
| `negative_control_shuffled_terminal` | port105's window total vs random draws of its own pre-crisis months |
| `gap_not_single_month` | is L spread over the window or produced by one month? |

## Two windows

The audit window is 1 Mar - 25 Sep 2026. The 2026-10-07 directive asked for 1 Mar 2025 - 25 Sep 2026. Both are
computed and reported (`measurements.window_audit_2026-03-01`, `measurements.window_directive_2025-03-01`); neither is
silently preferred.

## Synthetic fixtures

`tests/make_fixtures.py` writes a small invented raw directory in the ArcGIS JSON layout (4 ports, closed-form values),
used by `tests/test_forensic.py` for exact-answer unit tests, duplicate/gap injection, epoch-vs-string dates, negative
controls and an end-to-end run of `run_forensic.py`.
