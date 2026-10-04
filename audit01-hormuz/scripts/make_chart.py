#!/usr/bin/env python3
"""make_chart.py - AUDIT #1 chart from out/ tables. Writes out/audit01_chart.png (1600x900)."""
import json, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "out")
k = json.load(open(os.path.join(OUT, "key_numbers.json")))
bp = pd.read_csv(os.path.join(OUT, "bandar_e_pars_monthly.csv"))
bp["date"] = pd.to_datetime(bp.ym.astype(str), format="%Y%m")
prov = [json.loads(x) for x in open(os.path.join(ROOT, "data", "provenance.jsonl"))]
retrieved = max(p["retrieved_at_utc"] for p in prov).replace("T", " ").replace("Z", " UTC")[:-7] + " UTC"
doi = os.environ.get("AUDIT_DOI", "DOI pending")
b3 = k["BandarEPars_burst_days"]["3"]
rel = (k.get("portwatch_last_edit", {}).get("Daily_Ports_Data") or "n/a")[:10]

plt.rcParams.update({"font.size": 12})
fig, ax = plt.subplots(1, 2, figsize=(16, 9), dpi=100, gridspec_kw={"width_ratios": [1.5, 1]})
fig.suptitle("One terminal's implausible port-call bursts make up about half of PortWatch's Hormuz tanker gap",
             fontsize=17, fontweight="bold", x=0.01, ha="left")
ax[0].bar(bp.date, bp.portcalls_tanker, width=25, color="#333")
med = k["BandarEPars_median_calls_2019_2024"]
ax[0].axhline(med, color="#c00", lw=1)
ax[0].text(bp.date.min(), med + 18, f"2019-2024 median: {med:.0f} calls per month", color="#c00", fontsize=12)
if k["BandarEPars_202506_calls"]:
    ax[0].annotate(f"Jun 2025: {k['BandarEPars_202506_calls']} calls,\n"
                   f"{k['BandarEPars_202506_export_Mt']:.1f} Mt \"exported\"",
                   xy=(pd.Timestamp("2025-06-01"), k["BandarEPars_202506_calls"]),
                   xytext=(pd.Timestamp("2020-09-01"), 0.8 * k["BandarEPars_202506_calls"]),
                   arrowprops=dict(arrowstyle="->"), fontsize=12)
ax[0].set_title("1. Bandar-E Pars Terminal (Iran): tanker port calls per month", fontsize=13, loc="left")
ax[0].annotate("PortWatch FAQ flags AIS irregularities\nhere around 28 Aug 2024", xy=(pd.Timestamp("2024-08-01"), 140),
               xytext=(pd.Timestamp("2021-01-01"), 330), arrowprops=dict(arrowstyle="->"), fontsize=11)
ax[0].set_ylabel("tanker port calls per month")
lab = ["All 45 ports\ninside the Gulf", f"Without the\nterminal's {b3['days']}\nburst days", "Without\nthe terminal",
       "Without all\nIranian ports"]
vals = [k["L_Mt"], b3["L_without_burst_days_Mt"], k["L_excl_BandarEPars_Mt"], k["L_excl_Iran_Mt"]]
ax[1].bar(lab, vals, color=["#999", "#c00", "#c00", "#c00"])
for x, v in zip(lab, vals):
    ax[1].text(x, v + 0.2, f"{v:.2f}", ha="center", fontsize=13)
ax[1].set_ylim(0, 12); ax[1].set_ylabel("Mt (million metric tonnes)")
ax[1].tick_params(axis="x", labelsize=11)
a, b = (pd.Timestamp(x) for x in k["window"].split(".."))
w = f"{a.day} {a:%b} to {b.day} {b:%b %Y}"
ax[1].set_title(f"2. Gap, {w} (Mt):\nnet tanker cargo loaded inside the Gulf\nminus tanker cargo seen crossing Hormuz",
                fontsize=13, loc="left")
lo, hi = k["L_range_Mt"]
ax[1].text(0.98, 0.97, f"Range across filters: {lo:.1f} to {hi:.1f} Mt\n"
           f"Window from the 2nd month: {k['L_window_from_second_month_Mt']:.1f} Mt",
           transform=ax[1].transAxes, ha="right", va="top", fontsize=11)
fig.text(0.01, 0.015,
         f"Sources: Kpler; UN Global Platform; IMF PortWatch (portwatch.imf.org), Daily Ports Data and Daily Chokepoints Data "
         f"(chokepoint6), release of {rel}, retrieved {retrieved}.\nAggregation, netting and port exclusions are ours. PortWatch model "
         f"estimates in metric tonnes; PortWatch revises past data weekly. Burst day = 3+ tanker calls in one day.\n"
         f"Gap = unseen crossings OR cargo still afloat in the Gulf OR unrecorded discharge OR estimation error; "
         f"this data cannot separate them. Code: {doi}", fontsize=10.5, va="bottom")
plt.tight_layout(rect=[0, 0.11, 1, 0.95])
plt.savefig(os.path.join(OUT, "audit01_chart.png"), dpi=100)
print("chart: out/audit01_chart.png")
