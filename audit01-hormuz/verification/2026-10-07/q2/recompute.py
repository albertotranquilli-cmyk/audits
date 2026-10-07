#!/usr/bin/env python3
"""Independent recompute of AUDIT #1 key numbers (stdlib only; does NOT import the audit's analysis.py).
Input: raw PortWatch ArcGIS JSON as written by ../../../scripts/get_data.py (data/raw). Usage:
  python3 recompute.py [RAW_DIR]   (default: audit01-hormuz/data/raw). Expected input hashes: inputs_SHA256SUMS.
Output: recompute_out.json next to this script.
Definitions (own formulation, documented in ../REPORT.md):
  inside-Gulf port = 45 < lon < 56.3 and 23.5 < lat < 31.5 (box west of the Strait narrows; drops Red Sea,
                     Caspian, Gulf of Oman coast incl. Fujairah/Khor Fakkan/Sohar/Jask/Chabahar)
  E-I  = sum(export_tanker - import_tanker) over inside ports, months 2026-03..2026-09 (data end 2026-09-25)
  C    = sum(capacity_tanker) at chokepoint6, 2026-03-01..2026-09-25 (cut at last port day)
  gap  = (E-I) - C
"""
import json, glob, hashlib, os, statistics, sys
HERE = os.path.dirname(os.path.abspath(__file__))
RAW = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "..", "..", "data", "raw")
W0, W1 = "2026-03-01", "2026-09-25"
BP = "port105"

# input hashes vs the 2026-10-07 fresh run (informational: a later PortWatch release gives different files)
_exp = dict(l.split()[::-1] for l in open(os.path.join(HERE, "inputs_SHA256SUMS")) if l.strip())
_got = {n: hashlib.sha256(open(os.path.join(RAW, n), "rb").read()).hexdigest() for n in _exp if os.path.exists(os.path.join(RAW, n))}
print("inputs matching inputs_SHA256SUMS: %d/%d" % (sum(_got.get(n) == h for n, h in _exp.items()), len(_exp)))

def feats(stem):
    rows = []
    for p in sorted(glob.glob(os.path.join(RAW, f"{stem}_p*.json"))):
        d = json.load(open(p)); assert "error" not in d, p
        rows += [f["attributes"] for f in d["features"]]
    return rows

ports = feats("ports_db_gulf"); ch = feats("chokepoint6_daily"); pm = feats("ports_monthly_gulf"); bpd = feats("port105_daily")
inside = {p["portid"] for p in ports if 45 < p["lon"] < 56.3 and 23.5 < p["lat"] < 31.5}
iso = {p["portid"]: p["ISO3"] for p in ports}
name = {p["portid"]: p["portname"] for p in ports}
out = {"n_inside": len(inside), "inside_ports": sorted(f"{iso[p]}:{p}:{name[p]}" for p in inside)}

# integrity checks
keys = [(r["portid"], r["year"], r["month"]) for r in pm]
assert len(keys) == len(set(keys)), "duplicate port-month"
dates = [r["date"] for r in ch]; assert len(dates) == len(set(dates)), "duplicate chokepoint day"
out["ch_date_range"] = [min(dates), max(dates)]
out["pm_last_ym"] = max(r["year"] * 100 + r["month"] for r in pm)
out["pm_last_month_ndays_max"] = max(r["n_days"] for r in pm if r["year"] * 100 + r["month"] == out["pm_last_ym"])
out["inside_ports_with_rows"] = len({r["portid"] for r in pm} & inside)
out["inside_portmonth_rows"] = sum(1 for r in pm if r["portid"] in inside)

def ym(r): return r["year"] * 100 + r["month"]
win = [r for r in pm if r["portid"] in inside and 202603 <= ym(r) <= 202609]
E = sum(r["export_tanker"] for r in win); I = sum(r["import_tanker"] for r in win)
C = sum(r["capacity_tanker"] for r in ch if W0 <= r["date"] <= W1)
net = E - I; gap = net - C
def net_of(sel): return sum(r["export_tanker"] - r["import_tanker"] for r in win if sel(r))
bp_net = net_of(lambda r: r["portid"] == BP)
irn_net = net_of(lambda r: iso[r["portid"]] == "IRN")
out.update(E_Mt=E/1e6, I_Mt=I/1e6, net_Mt=net/1e6, C_Mt=C/1e6, gap_Mt=gap/1e6, ratio=net/C,
           ratio_excl_BP=(net-bp_net)/C, BP_net_window_Mt=bp_net/1e6, BP_share_of_gap_pct=100*bp_net/gap,
           gap_excl_BP_Mt=(gap-bp_net)/1e6, gap_excl_IRN_Mt=(gap-irn_net)/1e6,
           ch_days_in_window=sum(1 for r in ch if W0 <= r["date"] <= W1))

# baseline months 2019-01..2026-02: rho = net/C per month
Cm = {}
for r in ch:
    k = int(r["date"][:4]) * 100 + int(r["date"][5:7]); Cm[k] = Cm.get(k, 0) + r["capacity_tanker"]
Nm = {}
for r in pm:
    if r["portid"] in inside: Nm[ym(r)] = Nm.get(ym(r), 0) + r["export_tanker"] - r["import_tanker"]
base = {k: Nm[k] / Cm[k] for k in Nm if k <= 202602 and k in Cm}
out.update(baseline_months=len(base), baseline_rho_max=max(base.values()),
           baseline_rho_max_month=max(base, key=base.get), baseline_rho_gt1=sum(v > 1 for v in base.values()))

# Bandar-E Pars monthly
bpm = {ym(r): r for r in pm if r["portid"] == BP}
calls_1924 = [bpm[k]["portcalls_tanker"] for k in sorted(bpm) if k <= 202412]
out.update(BP_months_2019_2024_present=len(calls_1924), BP_median_calls_2019_2024=statistics.median(calls_1924),
           BP_mean_calls_2019_2024=statistics.mean(calls_1924),
           BP_202506_calls=bpm[202506]["portcalls_tanker"], BP_202506_export_Mt=bpm[202506]["export_tanker"]/1e6,
           BP_202506_import_Mt=bpm[202506]["import_tanker"]/1e6)
# daily
d = {r["date"]: r for r in bpd}
out["BP_20260228_calls"] = d.get("2026-02-28", {}).get("portcalls_tanker")
out["BP_top5_days_since_2025"] = sorted(((r["portcalls_tanker"], r["date"]) for r in bpd if r["date"] >= "2025-01-01"), reverse=True)[:5]
bw = [r for r in bpd if W0 <= r["date"] <= W1]
bw_net = sum(r["export_tanker"] - r["import_tanker"] for r in bw)
out["BP_daily_vs_monthly_net_diff_t"] = bw_net - bp_net
burst = {}
for k in (3, 5, 10):
    s = [r for r in bw if r["portcalls_tanker"] >= k]
    rm = sum(r["export_tanker"] - r["import_tanker"] for r in s)
    burst[k] = dict(days=len(s), removed_Mt=rm/1e6, gap_without_Mt=(gap-rm)/1e6, dates=[r["date"] for r in s])
out["burst"] = burst
months = list(range(202603, 202610))
med_net = statistics.median([bpm[k]["export_tanker"] - bpm[k]["import_tanker"] for k in sorted(bpm) if k <= 202412])
out["gap_excl_BP_excess_over_median_Mt"] = (gap - (bp_net - len(months) * med_net)) / 1e6
lo = min(out["gap_excl_BP_Mt"], out["gap_excl_IRN_Mt"]); hi = max(b["gap_without_Mt"] for b in burst.values())
out["range_Mt"] = [lo, hi]
# window from April
winA = [r for r in win if ym(r) >= 202604]
CA = sum(r["capacity_tanker"] for r in ch if "2026-04-01" <= r["date"] <= W1)
out["gap_from_Apr_Mt"] = (sum(r["export_tanker"] - r["import_tanker"] for r in winA) - CA) / 1e6
json.dump(out, open(os.path.join(HERE, "recompute_out.json"), "w"), indent=1)
for k, v in out.items():
    if k != "inside_ports": print(k, "=", v)
