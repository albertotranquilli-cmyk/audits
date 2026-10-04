#!/usr/bin/env python3
"""analysis.py - AUDIT #1: internal tanker mass balance of IMF PortWatch at the Strait of Hormuz.

E, I : tanker export / import estimates (t) at PortWatch ports inside the Strait (port module)
C    : tanker transit trade-volume estimates (t) at chokepoint6, both directions (chokepoint module)
L    : (E - I) - C over a window. With true values, L <= U + dS (U = unseen crossings, dS = change of laden
       cargo afloat inside the Gulf). With PortWatch estimates, L also contains the estimation errors of E and I
       (including discharges inside the Gulf that are not recorded). See README, "What this does NOT show".

Reads data/raw (downloaded by get_data.py). Writes tables to out/. Prints a neutral summary.
"""
import glob, json, os, sys
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, OUT = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "out")
os.makedirs(OUT, exist_ok=True)
pd.set_option("display.width", 220); pd.set_option("display.max_rows", 200)
CRISIS_START = 202603            # first full month after the 28 Feb 2026 strikes
BASE_END = 202602
BP = "port105"                   # Bandar-E Pars Terminal
BURST_THRESHOLDS = (3, 5, 10)    # tanker calls per day at port105 that define a "burst day"


def load(stem):
    files = sorted(glob.glob(os.path.join(RAW, f"{stem}_p*.json")))
    if not files:
        sys.exit(f"missing raw files for {stem}; run scripts/get_data.py")
    rows = []
    for p in files:
        d = json.load(open(p))
        if "error" in d:
            sys.exit(f"API error in {p}")
        rows += [f["attributes"] for f in d["features"]]
    return pd.DataFrame(rows)


def to_dt(s):
    return pd.to_datetime(s, unit="ms") if s.dtype != object else pd.to_datetime(s)


ports, ch, pm, bpd = load("ports_db_gulf"), load("chokepoint6_daily"), load("ports_monthly_gulf"), load("port105_daily")
assert not ch.duplicated("date").any() and not pm.duplicated(["portid", "year", "month"]).any()

# ---- 1. Ports inside the Strait: rule fixed in advance (country + coordinates)
def inside(r):
    if r.ISO3 in ("KWT", "BHR", "IRQ", "QAT"): return True
    if r.ISO3 == "SAU": return r.lon > 45        # Gulf coast only (Red Sea ports, e.g. Yanbu, lon < 43)
    if r.ISO3 == "ARE": return r.lon < 56.2      # excludes Fujairah, Khor Fakkan (Gulf of Oman)
    if r.ISO3 == "IRN": return r.lat < 31 and r.lon < 56.5   # excludes Caspian ports, Jask, Chabahar
    return False                                 # Oman: all ports outside
ports["inside"] = ports.apply(inside, axis=1)
INS = set(ports.loc[ports.inside, "portid"])
iso = ports.set_index("portid").ISO3
ports.sort_values(["inside", "ISO3", "portid"])[["portid", "portname", "ISO3", "inside"]].to_csv(
    os.path.join(OUT, "port_classification.csv"), index=False)

# ---- 2. Align windows: cut the chokepoint series at the last port day
pm["ym"] = pm.year * 100 + pm.month
last_ym = int(pm.ym.max()); last_days = int(pm.loc[pm.ym == last_ym, "n_days"].max())
ly, lm = divmod(last_ym, 100)
END = pd.Timestamp(ly, lm, last_days)
ch["d"] = to_dt(ch.date)
ch = ch[ch.d <= END].copy()
ch["ym"] = ch.d.dt.year * 100 + ch.d.dt.month
C = ch.groupby("ym").agg(C=("capacity_tanker", "sum"), n_transits=("n_tanker", "sum"), ch_days=("d", "count"))


def monthly(portset):
    g = pm[pm.portid.isin(portset)].groupby("ym").agg(E=("export_tanker", "sum"), I=("import_tanker", "sum"),
                                                   calls=("portcalls_tanker", "sum"), port_days=("n_days", "max"))
    t = g.join(C, how="inner")
    t["net"] = t.E - t.I
    t["rho"] = t.net / t.C
    return t


t = monthly(INS)
assert (t.port_days == t.ch_days).all(), "port and chokepoint day coverage differ"
base, crisis = t[t.index <= BASE_END], t[t.index >= CRISIS_START]
n_c, c_c = crisis.net.sum(), crisis.C.sum()
L = n_c - c_c

# ---- 3. Sensitivity: port sets x windows
sets = {"all45": INS, "excl_BandarEPars": INS - {BP}, "excl_Iran": {p for p in INS if iso[p] != "IRN"}}
months = sorted(crisis.index)
rows = []
for name, ps in sets.items():
    tt = monthly(ps)
    for a in range(len(months)):
        for b in range(a, len(months)):
            ms = months[a:b + 1]
            net, cc = tt.loc[ms].net.sum() / 1e6, tt.loc[ms].C.sum() / 1e6
            rows.append(dict(portset=name, start=ms[0], end=ms[-1], net_Mt=round(net, 3), C_Mt=round(cc, 3),
                             L_Mt=round(net - cc, 3)))
w = pd.DataFrame(rows)
w.to_csv(os.path.join(OUT, "window_sensitivity.csv"), index=False)
Lset = {k: w[(w.portset == k) & (w.start == months[0]) & (w.end == months[-1])].L_Mt.item() for k in sets}
tex = monthly(sets["excl_BandarEPars"]); tex_b = tex[tex.index <= BASE_END]
ratio_exBP = tex[tex.index >= CRISIS_START].net.sum() / c_c

# ---- 4. Bandar-E Pars: monthly history, burst days, excess over the 2019-2024 median
bp = pm[pm.portid == BP].set_index("ym")[["portcalls_tanker", "export_tanker", "import_tanker"]].copy()
bp["net"] = bp.export_tanker - bp.import_tanker
bp_med_calls = float(bp.loc[:202412].portcalls_tanker.median())
bp_med_net = float(bp.loc[:202412].net.median())
bp_crisis_net = float(bp.loc[CRISIS_START:].net.sum())
bp.assign(E_Mt=bp.export_tanker / 1e6, I_Mt=bp.import_tanker / 1e6, net_Mt=bp.net / 1e6)[
    ["portcalls_tanker", "E_Mt", "I_Mt", "net_Mt"]].round(4).to_csv(os.path.join(OUT, "bandar_e_pars_monthly.csv"))
bpd["d"] = to_dt(bpd.date)
bpd["net"] = bpd.export_tanker - bpd.import_tanker
ws = pd.Timestamp(CRISIS_START // 100, CRISIS_START % 100, 1)
bw = bpd[(bpd.d >= ws) & (bpd.d <= END)]
assert abs(bw.net.sum() - bp_crisis_net) < 1, "daily and monthly Bandar-E Pars totals differ"
burst = {}
for k in BURST_THRESHOLDS:
    sel = bw[bw.portcalls_tanker >= k]
    burst[k] = dict(days=int(len(sel)), net_Mt=sel.net.sum() / 1e6, L_without_burst_days_Mt=(L - sel.net.sum()) / 1e6)
excess = bp_crisis_net - len(months) * bp_med_net
# largest single days (2025-2026) for the thread; kept in out/ only (daily extract of source data)
top = bpd[bpd.d >= "2025-01-01"].nlargest(5, "portcalls_tanker")[["d", "portcalls_tanker", "net"]]

# ---- 5. Anomaly screen over all inside ports: port-months with calls > 10x the 2019-2024 median and > 30
med = pm[pm.ym <= 202412].groupby("portid").portcalls_tanker.median()
scr = pm[pm.portid.isin(INS)].assign(med=lambda x: x.portid.map(med).fillna(0).clip(lower=1))
scr = scr[(scr.portcalls_tanker > 10 * scr.med) & (scr.portcalls_tanker > 30)]
scr[["portid", "portname", "ym", "portcalls_tanker", "med"]].to_csv(os.path.join(OUT, "anomaly_screen.csv"), index=False)

# ---- 6. Save tables and key numbers
t.assign(E_Mt=t.E / 1e6, I_Mt=t.I / 1e6, net_Mt=t.net / 1e6, C_Mt=t.C / 1e6)[
    ["E_Mt", "I_Mt", "net_Mt", "C_Mt", "rho", "n_transits", "calls", "port_days"]].round(6).to_csv(
    os.path.join(OUT, "monthly_mass_balance.csv"))
lo = min(Lset["excl_Iran"], Lset["excl_BandarEPars"])
hi = max(v["L_without_burst_days_Mt"] for v in burst.values())
key = {
    "window": f"{ws.date()}..{END.date()}", "n_ports_inside": len(INS),
    "baseline_months": len(base), "baseline_rho_max": base.rho.max(), "baseline_rho_max_month": int(base.rho.idxmax()),
    "baseline_rho_median": base.rho.median(), "baseline_violations_rho_gt_1": int((base.rho > 1).sum()),
    "E_minus_I_Mt": n_c / 1e6, "C_Mt": c_c / 1e6, "ratio": n_c / c_c, "ratio_excl_BandarEPars": ratio_exBP,
    "L_Mt": L / 1e6, "L_share_pct": 100 * L / n_c,
    "L_excl_BandarEPars_Mt": Lset["excl_BandarEPars"], "L_excl_Iran_Mt": Lset["excl_Iran"],
    "BandarEPars_net_in_window_Mt": bp_crisis_net / 1e6, "BandarEPars_share_of_L_pct": 100 * bp_crisis_net / L,
    "BandarEPars_median_calls_2019_2024": bp_med_calls,
    "BandarEPars_202506_calls": int(bp.loc[202506, "portcalls_tanker"]) if 202506 in bp.index else None,
    "BandarEPars_202506_export_Mt": float(bp.loc[202506, "export_tanker"] / 1e6) if 202506 in bp.index else None,
    "BandarEPars_burst_days": {str(k): v for k, v in burst.items()},
    "L_excl_BandarEPars_excess_over_median_Mt": (L - excess) / 1e6,
    "L_range_Mt": [lo, hi],
    "L_window_from_second_month_Mt": w[(w.portset == "all45") & (w.start == months[1]) & (w.end == months[-1])].L_Mt.item(),
    "monthly_L_all45_Mt": {str(m): round((t.loc[m].net - t.loc[m].C) / 1e6, 3) for m in months},
    "C_by_month_Mt": {str(m): round(t.loc[m].C / 1e6, 3) for m in months},
    "BandarEPars_top_days_2025_2026": [{"date": str(r.d.date()), "tanker_calls": int(r.portcalls_tanker),
                                        "net_Mt": round(r.net / 1e6, 3)} for r in top.itertuples()],
    "anomaly_screen_ports": sorted(scr.portid.unique().tolist()),
}
rel = {}
for layer in ("Daily_Ports_Data", "Daily_Chokepoints_Data"):
    p = os.path.join(RAW, f"layerinfo_{layer}.json")
    if os.path.exists(p):
        ms = json.load(open(p)).get("editingInfo", {}).get("lastEditDate")
        rel[layer] = pd.Timestamp(ms, unit="ms").strftime("%Y-%m-%d %H:%M UTC") if ms else None
key["portwatch_last_edit"] = rel
json.dump(key, open(os.path.join(OUT, "key_numbers.json"), "w"), indent=1, default=float)

print("=== AUDIT #1: PortWatch internal tanker mass balance, Strait of Hormuz ===")
print(f"Ports inside the Strait: {len(INS)} | window {key['window']} (chokepoint series cut at the last port day)")
print(f"Baseline 2019-01..2026-02: {len(base)} months, rho=(E-I)/C max {base.rho.max():.3f} ({base.rho.idxmax()}),"
      f" median {base.rho.median():.3f}, months with rho>1: {(base.rho > 1).sum()}")
print(f"Window: E-I = {n_c/1e6:.2f} Mt, C = {c_c/1e6:.2f} Mt, ratio {n_c/c_c:.2f} (without Bandar-E Pars {ratio_exBP:.2f}),"
      f" L = {L/1e6:.2f} Mt")
print(f"Without Bandar-E Pars: {Lset['excl_BandarEPars']:.2f} Mt | without all Iranian ports: {Lset['excl_Iran']:.2f} Mt")
for k, v in burst.items():
    print(f"Without Bandar-E Pars burst days (>= {k} calls/day): {v['days']} days, {v['net_Mt']:.2f} Mt removed,"
          f" L = {v['L_without_burst_days_Mt']:.2f} Mt")
print(f"Without Bandar-E Pars excess over its 2019-2024 monthly median: L = {(L-excess)/1e6:.2f} Mt")
print(f"Range across these filters: {lo:.1f} to {hi:.1f} Mt (this window only; see window_sensitivity.csv)")
print(f"Window starting {months[1]}: L = {key['L_window_from_second_month_Mt']:.2f} Mt")
print(f"PortWatch release in use (layer lastEditDate): {rel}")
print(f"Anomaly screen (calls > 10x median and > 30): {key['anomaly_screen_ports']}")
