# PRE-REG #1: JODI China crude "refinery intake", August 2026

- **Registered (UTC):** `2026-10-08T20:15Z`. Planned: Thu 8 Oct 2026, 07:30 UTC (09:30 Rome). Fill this in, then commit, then hash, then post.
- **Line:** @AT4_80 public data audits. Companion to AUDIT #2 (`README.md`).
- **Status:** prediction about a number that has not been published yet.
  - JODI's file `primaryyear2026.csv` was last modified 22 Sep 2026, 07:18:47 UTC.
  - Checked 4 Oct 2026: it contains no 2026-08 rows for any country.

## 1. Hypothesis
For China, the JODI Oil World Database field "refinery intake" for crude oil is not a measured throughput. It is production + imports − exports (P + I − E). This holds in 70 of 70 months from Oct 2020 to Jul 2026 (AUDIT #2), and JODI's China country note says the figure is "calculated".

If that is right, the August 2026 value can be computed from other statistics before JODI publishes it.

## 2. Prediction
JODI, China (`CN`), `CRUDEOIL`, `REFINOBS`, `KTONS`, `2026-08`:
- **Point prediction: 56.10 Mt** (56,098 kt), which is about 13.25 mb/d at JODI's 7.32 bbl/t.
- **Pass window: 55.90 – 56.30 Mt.**

For reference only, this is not part of the test: NBS-surveyed crude processing for Aug 2026 is 59.07 Mt. The predicted JODI figure is therefore 2.97 Mt below NBS (window −3.17 to −2.77 Mt).

## 3. Inputs: all already public (disclosed)
| Input | Value | Source |
|---|---|---|
| P: crude production, Aug 2026 | 18.43 Mt | NBS, "Energy Production in August 2026" (16 Sep 2026), https://www.stats.gov.cn/english/PressRelease/202609/t20260916_1965338.html |
| I: crude imports, Aug 2026 | 37.928 Mt (3,792.8 × 10,000 t) | China Customs (GACC), "(6) China's Major Imports by Quantity and Value, Aug 2026", http://english.customs.gov.cn/Statics/1c29d265-76bf-4a44-9867-224c6ba7ec52.html |
| E: crude exports, Aug 2026 | 0.260 Mt (260,072,166 kg, HS 27090000) | Customs-based, via a secondary source: Blooming, "China Crude Petroleum Oil Trade Report … August 2026" (23 Sep 2026), https://www.bloominglobal.com/media/detail/china-crude-petroleum-oil-trade-report-import-and-export-data-for-august-2026. Cross-check: its +6.84% m/m implies July ≈ 243 kt, and JODI's July figure is 243 kt. |

56.098 = 18.43 + 37.928 − 0.260.

The authors have seen all three inputs, and Reuters published the same balance from official data on 15 Sep 2026. **What is unknown is only the figure JODI will publish.**

The test is whether JODI's published China refinery intake for August again equals P + I − E: whether it is again arithmetic on these statistics rather than a measured throughput.

## 4. Why this window
In the 34 monthly comparisons since Jan 2024 (AUDIT #2, `out/jodi_inputs_vs_nbs.csv`; production Jan 2024 – Jul 2026, and imports in 2024, the period when NBS quoted customs figures):
- JODI's production has matched NBS within 0.005 Mt;
- JODI's imports have matched the customs monthly figure within 0.005 Mt;
- JODI's July 2026 imports (35,726 kt) equal the customs figure (35.726 Mt).

If the mechanism holds, the expected error is therefore about 0.01 Mt. The ±0.20 Mt window is 40 times that, and leaves room for small customs revisions.

The prediction is not trivial. A value outside the window would mean that JODI's method or inputs for China have changed, and that would be news.

## 5. Scoring
Score on the first JODI file that contains `CN` / `2026-08`.

**Fails if any of these holds:**
- (a) `REFINOBS` (`KTONS`) is outside 55,900 – 56,300 kt;
- (b) JODI's own `INDPROD + TOTIMPSB − TOTEXPSB − REFINOBS` (`CRUDEOIL`, `KTONS`, 2026-08) differs from 0 by more than 5 kt;
- (c) JODI reports a non-zero crude stock change (`STOCKCH`, `CRUDEOIL` or `TOTCRUDE`) for China for Aug 2026.

**Partly void:** if JODI's China imports or exports for Aug 2026 differ from the inputs above by more than 0.20 Mt (a customs revision), (a) is not scored. Only (b) and (c) are scored, and this is reported as such.

**Void:** if China's Aug 2026 data are not in JODI by the 19 Nov 2026 update.

**Result:** published either way, with the file's Last-Modified header and its sha256.

## 6. Where and when to check
- **When:** JODI-Oil World Database first monthly update, **Wed 21 Oct 2026, 12:00 London (11:00 UTC, 13:00 Rome)**. If China is not in it, the supplementary updates and then 19 Nov 2026. Update calendar: https://www.jodidata.org/oil/support/update-calendar.aspx
- **File:** https://www.jodidata.org/_resources/files/downloads/oil-data/annual-csv/primary/primaryyear2026.csv
- **Rows:** `REF_AREA=CN`, `TIME_PERIOD=2026-08`, `ENERGY_PRODUCT=CRUDEOIL`, `FLOW_BREAKDOWN` in {`REFINOBS`, `INDPROD`, `TOTIMPSB`, `TOTEXPSB`, `STOCKCH`}, `UNIT_MEASURE=KTONS`. Also `TOTCRUDE`/`STOCKCH`.

## 7. What a pass would and would not show
- **It would show** that JODI's China "refinery intake" is computable from production and trade statistics before publication. It would be the 71st month in a row.
- **It would not show** which number, JODI or NBS, is closer to China's true refinery runs.
- **It would not show** how the JODI − NBS difference splits between stock change and volumes not captured by the NBS survey.
- **It would not show** that anyone misreported anything. JODI's country note discloses the calculation.

## 8. X post (≤ 280 characters as counted by X; the URL counts as 23)
Before posting, replace `{SHA12}` with the first 12 hex characters of the sha256 of this committed file (see §9).

```
PRE-REG #1 (sha256 {SHA12}): JODI's China "refinery intake", Aug 2026, will be 56.10 Mt (pass: 55.90–56.30) = NBS output 18.43 + customs imports 37.93 − exports 0.26, all public. Test: P+I−E again? NBS runs: 59.07 Mt. Resolves 21 Oct 12:00 London: https://www.jodidata.org/_resources/files/downloads/oil-data/annual-csv/primary/primaryyear2026.csv
```

276 characters by X's count (352 raw).

## 9. Integrity procedure (do it in this order)
1. Replace `{REGISTERED_UTC}` at the top with the UTC time of commit, for example `2026-10-08T07:25Z`. Change nothing else; `{SHA12}` stays literally in the file.
2. Commit this file to the public repo and note the commit hash.
3. Run `sha256sum PREREG_01.md` on the committed file and record the full hash in the commit message of a second commit, or in the repo `README`.
4. Post on X with `{SHA12}` replaced by the first 12 hex characters of that hash. The file cannot contain its own hash, so the hash lives in the post and in git.
5. After posting, do not edit this file. Corrections go in `ERRORS.md` with a timestamp.
