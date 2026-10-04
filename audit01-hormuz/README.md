# AUDIT #1: Strait of Hormuz, IMF PortWatch tanker data

An internal consistency check of two public IMF PortWatch series: tanker cargo **loaded at ports inside the
Gulf** and tanker cargo **seen crossing the Strait of Hormuz**, 1 March to 25 September 2026.

**Result, in one line.** PortWatch's port series records 10.23 Mt more net tanker cargo loaded inside the Gulf
than its Hormuz series records crossing. About half of that gap (5.28 Mt, 52%) comes from one terminal,
Bandar-E Pars (Iran), whose records contain implausible bursts of port calls. Without those records the gap is
**4.2 to 6.4 Mt for this window, depending on the filter**. It is negative (−1.9 Mt) if the window starts in April.

This is a **data-quality check, not an estimate of dark-fleet volumes** (see "What this does NOT show").

## Reproduce (one command)
```
bash run.sh            # downloads the PortWatch inputs if data/raw is empty, then rebuilds out/
bash run.sh --fresh    # always re-downloads
```
- Needs Python 3.11+ and internet access. `run.sh` creates `.venv` from `requirements.txt` (pinned versions).
- **No PortWatch data is shipped in this repository.** `scripts/get_data.py` downloads it from the public PortWatch
  (ArcGIS REST) API: about 15 polite requests, at least 6 s apart, with robots.txt checked first.
- The window end is pinned to `AUDIT_END=2026-09-25`, the last port day of the PortWatch release used for the
  thread. `AUDIT_END=auto` uses everything PortWatch publishes today.
- `scripts/check_records.py` compares the downloaded **records** (parsed JSON, keys sorted) with
  `manifests/raw_records_SHA256SUMS`. If they differ, PortWatch has revised the data and the numbers may move.
  PortWatch updates and revises past data **every Tuesday at 9:00 ET** (13:00 UTC while US daylight time applies).
- Outputs are written to `out/`. `derived/` holds the copy used for the thread, and `derived/SHA256SUMS` holds its hashes.

## Data used (PortWatch release of 2026-09-29; downloaded 2026-10-04 10:32 UTC)
| Layer | Fields | Use |
|---|---|---|
| `Daily_Ports_Data`, Gulf states + Oman, aggregated server-side to port × month | `portcalls_tanker`, `export_tanker`, `import_tanker` | E, I |
| `Daily_Ports_Data`, port105 (Bandar-E Pars Terminal), daily from 2024 | same | burst-day filter |
| `Daily_Chokepoints_Data`, chokepoint6 (Strait of Hormuz), daily | `n_tanker`, `capacity_tanker` | C |
| `PortWatch_ports_database` | port id, country, coordinates | which ports are inside the Strait |

**Definitions** (PortWatch item descriptions, read 2026-10-04):
- **Ports.** "The change in the vessel payload (in percentage points) multiplied by the vessel's deadweight tonnage
  (the maximum carrying capacity) in metric tons is the resulting trade flow (either import or export) in metric
  tons." Exports are dated at the ship's entry into the port.
- **Chokepoints.** `capacity_tanker` is "total trade volume (in metric tons) of all tankers transiting through the
  chokepoint at this date". It is the payload share estimated from draught × deadweight: **estimated cargo on board,
  not the ships' deadweight tonnage**.
- Since PortWatch's 2025 method update (IMF WP/25/93, Annex II), tankers travelling in ballast are set to zero
  cargo. Ballast transits therefore add (close to) nothing to C, unless the crew-reported AIS draught is stale.
- Both are model estimates. PortWatch calls them "preliminary".

## Method
1. **Ports inside the Strait (45).** A rule fixed in advance, by country and coordinates (`scripts/analysis.py`):
   - all of Kuwait, Bahrain, Iraq and Qatar;
   - Saudi Gulf coast (lon > 45);
   - UAE west of lon 56.2, so Fujairah and Khor Fakkan are excluded;
   - Iran south of lat 31 and west of lon 56.5, so Jask, Chabahar and the Caspian ports are excluded;
   - no Omani ports.

   Pipeline outlets that bypass Hormuz (Yanbu, Fujairah, Jask, Sohar) are therefore **outside**: bypass flows
   lower E and do not create a gap.
2. **Mass balance.** For a window, L = (E − I) − C, with E − I the net tanker exports of the 45 ports and C the tanker
   cargo in Hormuz transits, both directions. The chokepoint series is cut at the last port day.
   - With true values, cargo conservation gives L ≤ U + ΔS, where U is cargo in crossings the chokepoint series
     did not see and ΔS is the change in laden cargo afloat inside the Gulf.
   - Counting C in both directions makes this conservative.
3. **Baseline check.** In 86 pre-crisis months (2019-01 to 2026-02), ρ = (E − I)/C was at most 0.944 (Feb 2019),
   with a median of 0.584. It never exceeded 1.
4. **Anomaly screen.** Every inside port is screened for port-months with more than 10 × its 2019–2024 median of
   tanker calls and more than 30 calls. Only port105 (Bandar-E Pars Terminal) is flagged.
5. **Filters for that terminal** (window 1 Mar – 25 Sep 2026):
   - drop the terminal: L = 4.95 Mt;
   - drop only its burst days (3, 5 or 10 or more tanker calls in one day): L = 5.88, 6.04 or 6.37 Mt;
   - drop only its excess over its 2019–2024 median month: L = 5.63 Mt;
   - drop all Iranian ports: L = 4.21 Mt. This is a stricter test, not a correction, because it also removes
     real Iranian cargo.
6. **Window sensitivity.** L for every start and end month, for three port sets (`derived/window_sensitivity.csv`).

## Results (`derived/key_numbers.json`)
| Number in the thread | Value | Key |
|---|---|---|
| Net tanker exports, 45 inside ports | 33.66 Mt | `E_minus_I_Mt` |
| Tanker cargo seen crossing Hormuz, both ways | 23.43 Mt | `C_Mt` |
| Gap L | 10.23 Mt (30.4% of E − I) | `L_Mt` |
| Baseline max ratio / ratio in window | 0.94 / 1.44 (1.21 without the terminal) | `baseline_rho_max`, `ratio`, `ratio_excl_BandarEPars` |
| Bandar-E Pars median calls 2019–2024 | 5 a month | `BandarEPars_median_calls_2019_2024` |
| Bandar-E Pars, June 2025 | 677 calls, 42.8 Mt "exported" | `BandarEPars_202506_*` |
| Bandar-E Pars, 28 Feb 2026 | 89 calls in one day | `BandarEPars_top_days_2025_2026` |
| Bandar-E Pars net exports in window | 5.28 Mt, 52% of L | `BandarEPars_net_in_window_Mt` |
| On burst days (3+ calls) | 4.35 Mt on 8 days | `BandarEPars_burst_days` |
| Gap after filters | 4.2 to 6.4 Mt | `L_range_Mt` |
| Window Apr – 25 Sep | −1.92 Mt | `L_window_from_second_month_Mt` |
| C in August 2026 | 0.50 Mt | `C_by_month_Mt` |

The signal sits in March (L = 12.1 Mt in one month, when transits collapsed) and in August–September. From April to
July, C exceeds E − I by 6.7 Mt.

## What this does NOT show
- **It does not measure dark transits.** With PortWatch estimates, L = U + ΔS + (error in E) − (error in I). In words,
  the gap is cargo that crossed unseen, OR is still afloat inside the Gulf (for example tankers stranded at the start
  of the crisis), OR was discharged inside the Gulf without being recorded, OR is estimation error in PortWatch's
  series. This data cannot separate these. Bandar-E Pars shows that the error term can be large.
- **For scale.** The IEA (Oil Market Report, September 2026) puts August 2026 oil flows through Hormuz at
  7.6 mb/d, about 32 Mt in that month at 7.33 bbl/t. PortWatch's Hormuz series has 0.50 Mt of tanker cargo for August. Both
  PortWatch series see a small share of 2026 flows. Vortexa, Kpler and Windward measure dark transits directly with
  other data.
- **It depends on the window** (from −9.7 to +12.2 Mt across windows and port sets, `window_sensitivity.csv`). The 4.2–6.4 Mt range holds
  for 1 Mar – 25 Sep 2026 only.
- **Revisions.** PortWatch revises past data weekly and publishes no vintages.
  - It revised the Hormuz chokepoint boundary in March 2026; whether that revision was applied back to 2019 is not
    stated, and it matters for the 86-month baseline.
  - It added AIS-spoofing checks to the chokepoint series in July–August 2026. No such checks are documented for the
    port series. That is consistent with a port-side excess; we have not shown it is the cause.
  - August–September are the newest, least settled months.
- **It says nothing about how much Iran actually exports**, or about who causes GNSS interference.
- **Excluding a port is our choice.** It is not a PortWatch correction.

## Prior art and credits
- **IMF PortWatch FAQ** (https://portwatch.imf.org/pages/faqs) already notes "irregularities in the AIS data for the
  Bandar-E Pars Terminal around August 28, 2024". It also notes GPS jamming, AIS spoofing and vessels going dark in
  the Strait of Hormuz, and asks users to "use the data with care". This audit extends that flag to the 2025–2026
  bursts and to their effect on the Hormuz balance. PortWatch's country totals for Iran (`Daily_Trade_Data_REG`)
  include the same records: in June 2025, 42.81 Mt of Iran's 42.94 Mt of tanker exports were at this terminal.
- **Windward** documents GNSS interference redirecting AIS positions "to areas near Asaluyeh and Bandar Abbas" in
  June 2025, and a "surge in false port calls in Iran":
  - https://windward.ai/blog/middle-east-on-the-precipice-gps-jamming-in-the-arabian-gulf-and-strait-of-hormuz-disrupts-970-ships-daily/
  - https://windward.ai/knowledge-base/top-6-geopolitical-disruptions-q2-2025/

  It reported further surges after 28 Feb 2026 and on 7 Mar 2026:
  - https://windward.ai/blog/gps-jamming-disrupts-1100-ships-in-the-middle-east-gulf/
  - https://windward.ai/blog/gps-jamming-surges-in-the-middle-east-gulf-1650-ships-hit/
- **straitmonitor.com** (https://straitmonitor.com/methodology.html) compares tanker cargo loaded inside the Strait
  with tankers seen at the strait, and documents its method and code openly. That gap, it writes, "is ships running
  dark plus cargo leaving by the bypass routes". This audit builds on that comparison. We have not re-run their panels.
- **Vortexa** (https://www.vortexa.com/insights/dark-hormuz-transits), **Kpler** and **Windward** measure dark Hormuz
  transits directly with satellite and radio data.
- **IEA**, Oil Market Report, September 2026 (https://www.iea.org/reports/oil-market-report-september-2026), for scale.
- **Label note.** Several public trackers chart PortWatch's chokepoint `capacity` field. straitmonitor labels it
  "deadweight tonnage"/"dwt"; its "about 3.2 million deadweight tonnes" baseline is the 2025 mean of that field
  (3,218,243 t).
  hormuz.now labels it deadweight too. PortWatch defines the field as estimated cargo in metric tonnes: same numbers,
  wrong quantity name.

## Data terms and attribution
Sources: Kpler; UN Global Platform; IMF PortWatch (portwatch.imf.org). Aggregation, netting and port exclusions are ours.

- PortWatch data are **not** redistributed here and are **not** covered by this repository's license.
- `derived/` contains only tables we computed from them (aggregates, netting, filters). Raw inputs are re-downloaded
  by `run.sh`.
- Before reusing PortWatch data, check the IMF's copyright and usage terms
  (https://www.imf.org/en/About/copyright-and-terms). The IMF asks commercial users to contact it first.

## License
The code (`run.sh`, `scripts/`) is MIT-licensed (see `../LICENSE`). The license does not cover PortWatch data or the
third-party material quoted above.

## Errors
See `../ERRORS.md`. Found an error? Open an issue. Corrections are logged with the date (UTC) and, if you want, your name.

## Output hashes (`derived/SHA256SUMS`)
See `derived/SHA256SUMS` (sha256 of each derived file) and `manifests/raw_records_SHA256SUMS` (sha256 of the parsed
PortWatch records used).
