# Protocol-1: pre-registered evaluation of the open-data discovery engine

Repository: https://github.com/albertotranquilli-cmyk/audits. Language: English. Version: Protocol-1.
This file is frozen once committed. Its sha256 and an OpenTimestamps proof (`PROTOCOL.md.ots`) are recorded in
`engine/PROTOCOL_STATUS.md`. That status file can change; this file cannot (see section 10).

## 1. Question

Does an engine that generates checks automatically find anomalies in official data that hold up on data it has
not seen yet? And does it do so more often than the same pipeline run on a structured negative control? We count
the yield per unit of compute.

## 2. Fixed dates (stopping rule: no optional stopping)

| Event | Date (UTC) |
|---|---|
| Code freeze: the engine commit hash is written in `PROTOCOL_STATUS.md` | before 2026-10-07 00:00 |
| Start S | 2026-10-07 00:00 |
| Interim report 1 (descriptive only) | 2026-10-17 |
| Interim report 2 (descriptive only) | 2026-10-27 |
| End E (30 days; no check run after E counts) | 2026-11-06 00:00 |
| Classification lock (file hashed and stamped) | 2026-11-13 00:00 |
| Final report | 2026-11-14 |

- Interim reports give counts and costs only. They include no tests and no real-versus-control comparison, and they
  do not lead to any change in method.
- The protocol does not stop early, for success or for failure. The window is not extended for missed runs.
- If the code is not frozen before S, Protocol-1 never starts and is marked invalidated (section 10).
- If more than 30% of scheduled runs fail, Protocol-1 is marked failed (section 10).
- Runs happen only on the existing schedule (`.github/workflows/watch.yml`). Manual runs during the window are
  logged and excluded from the counts.

## 3. Data universe (fixed at S)

1. IMF PortWatch Daily Chokepoints Data, Strait of Hormuz (chokepoint6).
2. JODI Oil World Database, China crude oil (kb/d).
3. US EIA weekly commercial crude stocks excluding SPR (WCESTUS1).
4. UN Comtrade mirror pairs for HS 2709 and 2711 (the latest annual period available at S).
5. SEC EDGAR XBRL frames: us-gaap/Revenues/USD for CY2025Q1 and CY2025Q2 (requests carry a declared User-Agent and
   are rate-limited).
6. Scout-discovered CSVs from Zenodo and data.europa.eu. At most 3 per run, chosen in descending scout score with
   ties broken by id, and at most 5 MB each. Nothing else is added during the window.

## 4. Splits and leakage (enforced by code, with access logging)

**Rule for assigning splits**
- Time series: split A is every period up to 2026-10-06, as published on or before S. Split B is every period after
  2026-10-06, first published between S and E.
- Cross-sections (EDGAR, Comtrade, scout tables): each row goes to A if the first byte of
  `sha256(dataset_id + "|" + row_key)` is even, otherwise to B.
- Event classes (silent revision, deleted/changed file): the flag is the event observed at time t. Confirmation is a
  second, independent observation at least 7 days later. That means the revision persists in the next release, or
  the removal is confirmed both by a live HEAD request and by a second archive capture.

**How the code enforces it**
- Discovery, the generator and the allocator read only split A.
- Split B can be read only through a single function, `engine/splits.py: read_B(hypothesis_ids)`.
- That function refuses any hypothesis not already frozen in the ledger (id, check spec and sha256 of the A result,
  written in an earlier run).
- Every call appends a line to `engine/access_log.jsonl`: UTC time, run id, caller, dataset, hypothesis ids and the
  sha256 of the bytes read. The log is committed and timestamped every run.
- Any read of B that does not match a frozen hypothesis invalidates Protocol-1.
- B outcomes never feed back into the generator or the allocator during the window. Allocator rewards use split A
  flags only.

## 5. Check grammar (no hidden degrees of freedom)

A check is (test class, dataset, columns, parameters). Classes and parameters are fixed, and no class, parameter
or tolerance is added or changed during the window.

- **identity**: the forms A = B + C - D, A = B + C and A = B - C over the numeric columns.
  - At most 6 columns per dataset: the first 6 in lexicographic order that have at least 12 values.
  - Tolerance is min(0.5, 0.0005·|A|).
  - Only rows where all terms are present and pairwise distinct are counted.
  - Flag when the binomial tail against p0 = 0.01 gives p ≤ 0.001.
- **mirror**: robust z of log(M/X) - log(1.075) across pairs. Flag when the Bonferroni p ≤ 0.001.
- **revision**: a changed value for a key already published, against the stored fingerprint.
- **wayback**: a source file that went 404/410, or a data file whose digest changed, from the Wayback CDX.
- **benford**: first-digit chi-square (df 8). Applies when n ≥ 100 and the values span at least 2 orders of
  magnitude. Flag when p ≤ 0.001.
- **round**: excess of values that are multiples of 100 (in the column's own precision), against p0 = 0.01 with a
  binomial test. Flag when p ≤ 0.001.
- **repeat**: excess of identical consecutive values, against the collision probability of the column's empirical
  distribution. Flag when p ≤ 0.001.
- **jump**: the largest robust z of first differences. Applies when n ≥ 24. Flag when the Bonferroni p ≤ 0.001.
- **lastdigit**: last-digit chi-square (df 9). Applies when n ≥ 100 and values have at least 3 digits. Flag when
  p ≤ 0.001.

**Enumeration order**
- Datasets sorted by id.
- Classes in the order listed above.
- Columns sorted lexicographically, then combinations in lexicographic order.

**Caps on the number of checks**, truncated in enumeration order and never reshuffled:
- 300 per dataset;
- 2,000 per run;
- 20,000 distinct checks over the whole protocol.

**Allocator**
- Thompson sampling over classes with a Beta(1,1) prior. Reward is a split-A flag divided by mean cost in seconds.
- The time budget per run is fixed at 240 s (120 s on Mondays).
- The random seed is the first 8 bytes of `sha256("protocol-1|" + run_date_utc)`.
- The allocator decides only which checks run within the budget. It cannot change any check.

**Provenance**: every check is labelled `generated` or `human`. Human-specified checks are limited to those in
`engine/checks_human.json` at the code freeze.

## 6. Negative control (at least as structured as the real data)

- **Surrogates**: every real dataset gets one surrogate built by a fixed procedure. The surrogate keeps the real
  data's dates and keys, missingness mask, decimals and rounding precision, and the marginal distribution of each
  column.
  - Time series use multivariate IAAFT with the same random phases across columns, which keeps autocorrelation and
    cross-correlation.
  - Cross-sections permute rows within strata, which keeps their joint rows.
- **Identities**: accounting identities that the publisher's documentation states (with a link recorded at the code
  freeze) are imposed in the surrogate as well.
- **Same treatment**: control datasets go through the identical grammar, caps, split rules and allocator. They get
  the same per-run budget, in a separate pool.
- **Blinding**: control and real datasets carry blinded ids (hash-based), so reviewers cannot tell them apart.

## 7. Outcomes and blind classification

- A split-A flag becomes hypothesis H_i, frozen in the ledger before B is read.
- Outcome on B, decided by code:
  - **confirmed**: the same check on B has p ≤ 0.01 in the same direction, or for event classes the independent
    second observation in section 4 is met;
  - **not confirmed**: otherwise.
- Human/agent review then labels each confirmed H_i **trivial** or **non-trivial** and records `false_positive` when
  the evidence shows an artefact. Reviewers see column names, the check spec and the A and B outputs. They do not
  see the publisher, the dataset tier, the weight w_i, or the real/control label.
- The weight w_i is assigned blind by a fixed rule from the dataset tier, applied by code only after the
  classification file is locked:
  - w = 3 for official energy statistics (EIA, JODI, IEA, IMF PortWatch);
  - w = 2 for official trade or financial statistics (UN Comtrade, SEC EDGAR);
  - w = 1 for scout-discovered datasets.

## 8. Analysis (only at the final report)

- **Primary**: the confirmed non-trivial rate (confirmed non-trivial H_i ÷ checks run), real against control,
  one-sided Fisher exact test at α = 0.05. **Success** requires p < 0.05 **and** at least 3 confirmed non-trivial
  discoveries in the real data. Anything else is failure.
- **Secondary**:
  - confirmed non-trivial discoveries per runner-hour;
  - the weighted version Σ w_i per runner-hour;
  - false-positive rate = false_positive ÷ reviewed;
  - share of confirmed discoveries that were auto-generated;
  - yield per class.
- All checks are reported, including failures and checks that errored. The ledger (`engine/ledger.jsonl`) is
  append-only.

## 9. What this protocol does not claim

A confirmed anomaly is a statistical irregularity that held up out of sample. It is not evidence of intent or
misreporting. Each one needs an independent source before it is published as a finding.

## 10. No retroactive modification

No retroactive modification. If a methodological flaw is found during the 30 days, Protocol-1 is NOT corrected: it is
marked failed/invalidated, the reason is documented in engine/PROTOCOL_STATUS.md, and a Protocol-2 is issued with a
new hash and timestamp. Every version and its status are preserved.
