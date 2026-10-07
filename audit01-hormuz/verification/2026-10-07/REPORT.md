# AUDIT #1 (Strait of Hormuz): independent verification, 2026-10-07

Scope: an independent check of (Q1) the meaning of the IMF PortWatch fields the audit sums, including the wording of
thread post 8, and (Q2) the published key numbers, recomputed with new code that does not import `scripts/analysis.py`.
All sources are public; every request was read-only. Source URLs, SHA-256 hashes and Wayback copies: [SOURCES.md](SOURCES.md).

**Release.** All numbers below are tied to the PortWatch weekly release of **6 October 2026** (ArcGIS layer
`lastEditDate`: Daily_Ports_Data 2026-10-06 18:41 UTC, Daily_Chokepoints_Data 2026-10-06 12:09 UTC). The layer metadata
fetched for this verification on 2026-10-07 21:12 UTC is byte-identical to the metadata recorded by the audit's fresh run
(2026-10-07 08:52 UTC), copies in [metadata/](metadata/). PortWatch revises past data weekly; the **next revision is due
Tuesday 13 October 2026, 9:00 ET**, after which a rerun may give different numbers.

## Summary

| Question | Result |
|---|---|
| Q1. Meaning of `capacity_tanker` (chokepoints) and `export_tanker` / `import_tanker` (ports) | **Confirmed**: model estimates of cargo in metric tons (draught-based payload share x deadweight tonnage), not nominal deadweight tonnage. For tankers, payloads below a ballast threshold are set to zero under the 2025 ballast-water adjustment. |
| Post 8 wording | All five clauses supported by primary sources, with the nuances listed below. |
| Q2. Published numbers | **All reproduced** from the fresh-run inputs and, separately, from server-side sums on the live API. |

## Q1. What the summed fields mean

Fields used by the audit (`scripts/get_data.py`, `scripts/analysis.py`): at chokepoint6 (Strait of Hormuz)
`capacity_tanker` and `n_tanker`; at ports `export_tanker`, `import_tanker`, `portcalls_tanker`. PortWatch has no
`capacity_export` / `capacity_import` fields. Port fields are a payload **change** x DWT per port call; chokepoint fields
are a payload **level** x DWT at the time of transit.

### (a) ArcGIS layer metadata

`Daily_Ports_Data/FeatureServer/0?f=json` and `Daily_Chokepoints_Data/FeatureServer/0?f=json` carry **no field
descriptions**: every alias equals the field name (e.g. `capacity_tanker`, alias `capacity_tanker`,
`esriFieldTypeInteger`, description `null`), and the layer `description` is empty. Units and definitions appear only in
the ArcGIS **item** descriptions.

Chokepoints item `3da2b9ca97684916b75c4013f95d18ab`:

> Trade Volume Estimates: as described in the paper, we use the vessel information (length, width, draft, capacity, block coefficient) to estimate the payload (or utilization rate) of the vessel when transiting through the chokepoint. The vessel payload (in percentage points) multiplied by the vessel's deadweight tonnage (the maximum carrying capacity) in metric tons is the resulting trade volume estimate in metric tons carried by the ship.

> capacity_tanker: total trade volume (in metric tons) of all tankers transiting through the chokepoint at this date.

> capacity: total trade volume (in metric tons) of all ships transiting through the chokepoint at this date.

Ports item `83b1bbc7b3354c5fb1f40673bb8f852e`:

> The change in the vessel payload (in percentage points) multiplied by the vessel's deadweight tonnage (the maximum carrying capacity) in metric tons is the resulting trade flow (either import or export) in metric tons.

> export_tanker: total export volume (in metric tons) of all tankers entering the port at this date.

> import_tanker: total import volume (in metric tons) of all tankers entering the port at this date.

### (b) PortWatch documentation and IMF working papers

PortWatch Data & Methodology page, changelog, section "2025", "Methodological Change":

> The trade estimates have been adjusted to account for ballast water in the estimation.

Same page: "Download daily chokepoint transit calls and preliminary transit trade volume estimates for 28 major chokepoints worldwide."

IMF WP/25/93, *Nowcasting Global Trade from Space* (Arslanalp et al., May 2025), pp. 5-6:

> Absent an adjustment, this can lead AIS-based estimates to overstate the volume of cargo carried during a voyage (because part of the cargo is ballast water) [...] we classify vessels into those travelling "in ballast", "with ballast" and "laden (loaded)" to estimate their actual cargo payloads. Based on this, we observe transit and trade estimates closer to official data at specific chokepoints and ports.

Annex II, equation A2.1 (Type 1 vessels = tankers and dry bulk carriers): adjusted payload = 0 if the unadjusted
payload is at or below b + f + e ("In ballast"); otherwise unadjusted payload minus fuel f ("Laden (without ballast)").
Here b = ballast water, f = fuel, e = measurement error, each as a share of DWT (footnote 15: e = 15% of DWT for Type 1).
Page 4: "The transit volume data are expressed in metric tons."

IMF WP/21/225, *Tracking Trade from Space: An Application to Pacific Island Countries* (Arslanalp, Koepke, Verschuur,
2021), pp. 20-21: payload (utilization rate) from reported draught, length, width, block coefficient and DWT
(equation 1), and

> the utilization rate already captures the ballast water in the ship—that is, we do not need to make a separate assumption on ballast water levels.

That is the pre-2025 method, with no zeroing of ballast voyages.

**PortWatch-side documentation inconsistency.** Both ArcGIS items still cite **only the 2021 paper (WP/21/225)** as the
methodology source ("as described in the paper"). The ballast-water adjustment now in use is described only in the
changelog and in WP/25/93.

PortWatch FAQ: "We are also aware of specific anomalies at certain ports, such as irregularities in the AIS data for the
Bandar-E Pars Terminal around August 28, 2024 [...]" and "Draft information, which we use to estimate imports and
exports, are manually updated by the crew and may be erroneous."

### Post 8, clause by clause

> PortWatch's "capacity" field is estimated cargo on board in metric tonnes: draught-based payload share x deadweight, with ships in ballast set to zero since a 2025 method update. Some trackers label it deadweight tonnage: same numbers, wrong quantity name.

| Clause | Status | Basis and nuance |
|---|---|---|
| "estimated cargo on board in metric tonnes" | Supported | Item: "trade volume estimate in metric tons carried by the ship". PortWatch calls these estimates "preliminary". Paraphrase, not a verbatim quote. |
| "draught-based payload share x deadweight" | Supported | Item description; WP/21/225, equation 1. |
| "ships in ballast set to zero" | Supported | WP/25/93, equation A2.1, for tankers. Nuances: the threshold includes an error band (e = 15% of DWT), so lightly laden tankers are also counted as zero; laden tankers have fuel subtracted. Not mentioned in the ArcGIS item descriptions. |
| "since a 2025 method update" | Supported | Changelog "2025 ... Methodological Change"; WP/25/93 (May 2025). Nuances: the changelog gives no month and says "trade estimates" without naming the chokepoint series; WP/25/93 explicitly applies the adjustment to transit volumes (Panama Canal example) and shows adjusted series back to 2019. "Since" therefore refers to the method change, not to a cut-off in the data. |
| "Some trackers label it deadweight tonnage: same numbers, wrong quantity name" | Supported | straitmonitor.com (checked 2026-10-07): its code reads `capacity` / `capacity_tanker` from `Daily_Chokepoints_Data` and labels it `'Daily deadweight tonnage vs. 2025 baseline', unit: 'dwt'`; its page states "Capacity is the combined deadweight tonnage of the vessels counted." Its published daily `n_tanker` and `capacity_tanker` equal the PortWatch values on 633 of 633 common days (2025-01-01 to 2026-09-25): [q2/straitmonitor_check.txt](q2/straitmonitor_check.txt). |

**Verdict Q1: CONFIRMED.** No source defines these fields as nominal deadweight tonnage.

## Q2. Independent recomputation

- [q2/recompute.py](q2/recompute.py): standard library only; does not import the audit code. It defines inside-Gulf
  ports with its own rule (a box west of the Strait narrows: 45 < lon < 56.3 and 23.5 < lat < 31.5), which selects
  the same 45 ports as the audit's country-plus-coordinates rule. Inputs: the raw PortWatch responses of the audit's
  fresh run on 2026-10-07 (08:52-08:56 UTC). Their hashes are in [q2/inputs_SHA256SUMS](q2/inputs_SHA256SUMS) and match
  the run's provenance log. Raw PortWatch data are not shipped in this repository; `scripts/get_data.py` downloads them.
  Output: [q2/recompute_out.json](q2/recompute_out.json).
- [q2/api_crosscheck.py](q2/api_crosscheck.py): a second, separate path. Six server-side statistics queries against the
  live ArcGIS API, written independently of `get_data.py`. Output: [q2/api/summary.json](q2/api/summary.json);
  query URLs, times and response hashes in [q2/api/provenance.jsonl](q2/api/provenance.jsonl).
  Both paths agree to the tonne.

| Published number | Recomputed | Status |
|---|---|---|
| Bandar-E Pars Terminal (port105), June 2025: 677 tanker calls | 677 | reproduced |
| Bandar-E Pars, June 2025: 42.8 Mt "exported" | 42.808 Mt `export_tanker`. This is **gross** export: imports 7.60 Mt, **net 35.21 Mt** | reproduced (gross) |
| Median 2019-24 monthly tanker calls at port105: 5 | 5.0 (72 of 72 months present; mean 8.6) | reproduced |
| 89 tanker calls on 2026-02-28 | 89 | reproduced |
| Net tanker exports, 45 ports inside the Gulf, 1 Mar-25 Sep 2026: 33.65 Mt | 33.6508 Mt (exports 54.554, imports 20.904) | reproduced |
| Tanker cargo crossing Hormuz, both directions: 23.43 Mt | 23.4282 Mt (209 days) | reproduced |
| Gap: 10.22 Mt | 10.2226 Mt | reproduced |
| Exports/crossings ratio 1.44; pre-crisis max 0.94 in 86 months | 1.436; 0.944 (Feb 2019), 86 months, none above 1 | reproduced |
| Terminal contribution: 5.28 Mt, 52% of the gap | 5.2810 Mt, 51.7% | reproduced |
| Without the terminal: 4.94 Mt | 4.9416 Mt | reproduced |
| Without all Iranian ports: 4.20 Mt | 4.2034 Mt | reproduced |
| Without the terminal's 4-8 burst days: 5.9-6.4 Mt | >= 3 calls/day: 8 days, 5.868; >= 5: 6 days, 6.030; >= 10: 4 days, 6.367 | reproduced |
| Range: 4.2-6.4 Mt | 4.203-6.367 Mt | reproduced |
| Window from April: -1.9 Mt | -1.922 Mt | reproduced |

### Definitional choices

These match the audit's own definitions:

- Window: calendar months March-September 2026, with port data ending 2026-09-25. The chokepoint series is cut at the
  same day.
- Net exports: `export_tanker - import_tanker`. Crossings: `capacity_tanker` summed over both directions.
- Burst day: a port105 day with at least k tanker calls, k in {3, 5, 10}. The 5.9-6.4 Mt range depends on this choice.
- Median: taken over the monthly values for 2019-01 to 2024-12. All 72 months are present, so no zero-filling question
  arises.
- Port-month values: server-side sums of daily rows. The daily port105 total for the window equals the monthly total
  exactly.

## Reproduce

```
bash run.sh --fresh                                          # from audit01-hormuz/: downloads data/raw
python3 verification/2026-10-07/q2/recompute.py data/raw     # prints "inputs matching inputs_SHA256SUMS: n/14"
python3 verification/2026-10-07/q2/api_crosscheck.py         # live API; results follow the current release
```

After the 13 October 2026 release, input hashes and numbers may differ; that reflects PortWatch revisions, not a code change.
File hashes for this directory: [SHA256SUMS](SHA256SUMS).
