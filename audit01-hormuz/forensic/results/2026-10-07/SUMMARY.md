# Forensic run 2026-10-07: summary

- Code: commit `0e601dbcb4c15a213534f2a8462c5baf91be205b` (clean tree), recorded in `manifest.json -> code`.
- Inputs: fresh download by `scripts/get_data.py --fresh`, 2026-10-07 21:48-21:50 UTC; PortWatch release
  Daily_Ports_Data 2026-10-06 18:41 UTC, Daily_Chokepoints_Data 2026-10-06 12:09 UTC. URLs, times and SHA-256 per file
  in `manifest.json -> inputs` (all 14 match `data/provenance.jsonl`). Raw PortWatch data are not committed.
- Status counts: **12 PASS, 4 FAIL, 3 UNKNOWN** (`results.json`). Unit tests: 12/12 OK (`unittest_output.txt`).

## Observed (from the data and documents named in results.json)

| Check | Status | Observed |
|---|---|---|
| Field schema | PASS | `capacity_tanker`, `n_tanker`, `export_tanker`, `import_tanker`, `portcalls_tanker` are integer fields; the layer schema has no field descriptions |
| Field definition | PASS | Both ArcGIS item descriptions (fetched 21:49-21:50 UTC) contain the metric-ton, payload x DWT definitions; both cite only IMF WP/21/225, not WP/25/93 |
| Ballast zeroing applied | UNKNOWN | Documented (WP/25/93, 2025 changelog); not observable in daily aggregates |
| Units / aggregation | PASS | All values non-negative integers; port105 monthly sums equal daily sums for every month compared |
| Published numbers | PASS | All 21 published values reproduce at their published rounding. 42.8 Mt is gross June 2025 export; net is 35.21 Mt |
| Duplicate keys | PASS | 0 duplicate port-month keys, chokepoint dates, port105 dates or identical rows |
| Duplicate vessel events | UNKNOWN | No vessel identifiers in the public layers |
| Row completeness | PASS | 0 missing chokepoint dates; 0 absent or short port-months for the 45 ports |
| AIS signal gaps | UNKNOWN | 54 of 209 audit-window days show 0 tanker transits at chokepoint6 (none before 2026-03); a 0 row cannot be told apart from no traffic |
| Revision sensitivity | PASS | Gap 10.2302 Mt (release 2026-09-29, downloaded 2026-10-04) vs 10.2226 Mt (release 2026-10-06): delta 0.0075 Mt. The 2026-10-07 08:52 UTC download and this one have identical records (fingerprint equal) although 6 files differ by 2 bytes |
| Denominator | PASS | Window ratio exceeds its pre-crisis monthly maximum both in tonnes (1.44 vs 0.94) and in counts (tanker calls / tanker transits 4.69 vs 1.08) |
| Alternative port sets | PASS | Audit-window gap > 0 for all 7 non-adversarial sets (4.20 to 13.49 Mt) |
| Alternative windows | **FAIL** | Sign depends on window start: e.g. from 2026-04 -1.92, from 2026-07 +1.94, from 2025-03 -247.68 Mt |
| Pre-crisis negative control | PASS | Max (E-I)/C over 80 pre-crisis 7-month windows: 0.76 |
| Leave-one-port-out | **FAIL** | port105 ranks 5th by absolute contribution (Juaymah 8.78, Jubail 7.36, Basrah Oil Terminal 6.83, Ras Laffan 6.03, port105 5.28 Mt) |
| Excess over own baseline (post hoc) | PASS | port105 ranks 1st (4.60 Mt), narrowly ahead of Jebel Ali (4.52 Mt) |
| Single month | **FAIL** | March 2026 alone: +12.14 Mt (119% of the window gap); Apr-Jul net negative |
| Shuffled terminal | **FAIL** | port105's 5.28 Mt is not unusual against its own pre-crisis months: p = 0.34; 16 of 80 contiguous 7-month pre-crisis blocks are at least as large (max 69.36 Mt, mid-2025) |

## The two windows (both computed; neither preferred)

| | 1 Mar - 25 Sep 2026 (audit) | 1 Mar 2025 - 25 Sep 2026 (directive) |
|---|---|---|
| Net tanker exports, 45 ports | 33.65 Mt | 592.75 Mt |
| Tanker cargo crossing Hormuz | 23.43 Mt | 840.42 Mt |
| Gap L | 10.22 Mt | -247.68 Mt |
| Ratio (E-I)/C | 1.44 | 0.71 |
| port105 net in window | 5.28 Mt | 81.14 Mt |
| L without port105 | 4.94 Mt | -328.82 Mt |
| L without Iranian ports | 4.20 Mt | -328.79 Mt |
| L without port105 burst days (>=3/5/10 calls) | 5.87 / 6.03 / 6.37 Mt (8/6/4 days) | -327.28 / -326.81 / -325.80 Mt (54/47/42 days) |
| Baseline months, max monthly ratio | 2019-01..2026-02: 86, 0.944 | 2019-01..2025-02: 74, 0.944 |

## Hypotheses (not tested by this run)

- The March 2026 concentration fits cargo exported (dated at port entry) but not yet crossed, i.e. afloat inside the
  Gulf at the cut-off, and/or transits not seen by AIS. The data cannot separate these.
- The 54 zero-transit days fit either a real halt in traffic or AIS reception or spoofing gaps.
- port105 bursts predate the crisis (2024-08, 2024-10, 2025-06..10, 2026-02). Their size relative to the window
  points to a chronic data artefact rather than a crisis-specific signal; it does not show what the bursts are.
- In normal months port-side net exports cover only ~58% of chokepoint tanker cargo (median ratio). So L is only
  informative when chokepoint traffic collapses, and a window that includes 12 normal months (the directive window)
  is dominated by that structural shortfall.
