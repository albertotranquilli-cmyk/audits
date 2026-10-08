#!/usr/bin/env python3
"""run_forensic.py - AUDIT #1 forensic checks with a machine-readable manifest (stdlib only).

Usage (from audit01-hormuz/):
  python3 scripts/get_data.py --fresh                      # fresh PortWatch inputs -> data/raw (+ data/provenance.jsonl)
  python3 forensic/run_forensic.py --raw data/raw --out forensic/out [--fetch-docs] [--compare LABEL=DIR ...]

Writes <out>/results.json (checks with PASS/FAIL/UNKNOWN), <out>/manifest.json (inputs, code, dependencies,
output hashes) and <out>/SHA256SUMS. Exit code 0 unless the run itself breaks; check outcomes live in the JSON.
Status semantics: PASS = the stated hypothesis holds on the observed data; FAIL = it does not; UNKNOWN = not
observable with these inputs (or not attempted). A FAIL in a robustness/falsification check is a finding, not a crash.
"""
import argparse, hashlib, html, importlib.metadata as md, json, os, platform, re, subprocess, sys, time
import urllib.parse, urllib.request, urllib.robotparser
import datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import core  # noqa: E402

UA = os.environ.get("AUDIT_UA", "audit01-hormuz-forensic/1.0 (read-only research script)")
ITEMS = {"Daily_Chokepoints_Data": "3da2b9ca97684916b75c4013f95d18ab", "Daily_Ports_Data": "83b1bbc7b3354c5fb1f40673bb8f852e"}
DOC_STRINGS = {
    "Daily_Chokepoints_Data": [
        "capacity_tanker: total trade volume (in metric tons) of all tankers transiting through the chokepoint at this date.",
        "deadweight tonnage (the maximum carrying capacity) in metric tons is the resulting trade volume estimate in metric tons carried by the ship",
        "to estimate the payload (or utilization rate) of the vessel when transiting through the chokepoint"],
    "Daily_Ports_Data": [
        "export_tanker: total export volume (in metric tons) of all tankers entering the port at this date.",
        "import_tanker: total import volume (in metric tons) of all tankers entering the port at this date.",
        "The change in the vessel payload (in percentage points) multiplied by the vessel"],
}
# Numbers as published in the X thread (posted 2026-10-07 19:27 Europe/Rome), computed on the 2026-10-06 release.
PUBLISHED = {
    "net_45_ports_Mt": (33.65, 2), "C_Mt": (23.43, 2), "gap_Mt": (10.22, 2), "ratio": (1.44, 2),
    "baseline_rho_max": (0.94, 2), "baseline_months": (86, 0), "port105_202506_calls": (677, 0),
    "port105_202506_export_gross_Mt": (42.8, 1), "port105_median_calls_2019_2024": (5, 0),
    "port105_20260228_calls": (89, 0), "port105_net_window_Mt": (5.28, 2), "port105_share_of_gap_pct": (52, 0),
    "gap_excl_port105_Mt": (4.94, 2), "gap_excl_Iran_Mt": (4.20, 2), "burst_gap_min_Mt": (5.9, 1),
    "burst_gap_max_Mt": (6.4, 1), "burst_days_min": (4, 0), "burst_days_max": (8, 0), "range_low_Mt": (4.2, 1),
    "range_high_Mt": (6.4, 1), "gap_from_April_Mt": (-1.9, 1),
}
AUDIT_START, DIRECTIVE_START = 202603, 202503


def sha(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()


def now():
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def check(cid, question, hypothesis, observed, status, evidence=None):
    assert status in ("PASS", "FAIL", "UNKNOWN")
    return dict(id=cid, question=question, hypothesis=hypothesis, observed=observed, status=status, evidence=evidence)


def git(*a):
    try:
        return subprocess.run(["git", *a], cwd=HERE, capture_output=True, text=True, timeout=30).stdout.strip()
    except Exception:
        return None


# ------------------------------------------------------------ key numbers for one raw set and one window
def key_numbers(data, start_ym):
    sets, by = core.port_sets(data["ports"])
    ins = sets["audit_45"]
    end = core.data_end(data["pm"])
    end_ym = int(end[:4]) * 100 + int(end[5:7])
    start_date = f"{start_ym // 100:04d}-{start_ym % 100:02d}-01"
    b = core.balance(data, ins, start_ym)
    bx = core.balance(data, sets["excl_port105"], start_ym)
    bi = core.balance(data, sets["excl_Iran"], start_ym)
    base_months = [m for m in core.ym_range(201901, start_ym - 1 if start_ym % 100 != 1 else start_ym - 89)]
    rho = core.monthly_rho(data, ins, base_months)
    bp_net = b["net_t"] - bx["net_t"]
    out = dict(window=f"{start_date}..{end}", n_ports=len(ins), E_Mt=b["E_t"] / 1e6, I_Mt=b["I_t"] / 1e6,
               net_Mt=b["net_t"] / 1e6, C_Mt=b["C_t"] / 1e6, gap_Mt=b["L_t"] / 1e6, ratio=b["ratio"],
               ratio_excl_port105=bx["net_t"] / b["C_t"], port105_net_Mt=bp_net / 1e6,
               port105_share_of_gap_pct=100 * bp_net / b["L_t"] if b["L_t"] else None,
               gap_excl_port105_Mt=bx["L_t"] / 1e6, gap_excl_Iran_Mt=bi["L_t"] / 1e6,
               baseline=f"{base_months[0]}..{base_months[-1]}", baseline_months=len(rho),
               baseline_rho_max=max(rho.values()), baseline_rho_max_month=max(rho, key=rho.get),
               baseline_months_rho_gt_1=sum(v > 1 for v in rho.values()))
    if data["bpd"] and core.daily_covers(data, start_date, end):
        bursts = {}
        for k in (3, 5, 10):
            sel, rm = core.burst_days(data, start_date, end, k)
            bursts[str(k)] = dict(days=len(sel), removed_Mt=rm / 1e6, gap_without_Mt=(b["L_t"] - rm) / 1e6)
        out["burst_days"] = bursts
        out["range_Mt"] = [min(out["gap_excl_port105_Mt"], out["gap_excl_Iran_Mt"]),
                           max(v["gap_without_Mt"] for v in bursts.values())]
    else:
        out["burst_days"] = "UNKNOWN: port105 daily rows do not cover the window"
    bpm = {r["ym"]: r for r in data["pm"] if r["portid"] == core.BP}
    med_net = core.median([bpm[m]["export_tanker"] - bpm[m]["import_tanker"] for m in bpm if m <= 202412])
    n_m = len(core.ym_range(start_ym, end_ym))
    out["gap_excl_port105_excess_over_2019_2024_median_Mt"] = (b["L_t"] - (bp_net - n_m * med_net)) / 1e6
    return out


def port105_facts(data):
    bpm = {r["ym"]: r for r in data["pm"] if r["portid"] == core.BP}
    calls = [bpm[m]["portcalls_tanker"] for m in sorted(bpm) if m <= 202412]
    d = {r["date"]: r for r in data["bpd"]}
    j = bpm.get(202506)
    return dict(months_2019_2024_present=len(calls), median_calls_2019_2024=core.median(calls),
                calls_202506=j and j["portcalls_tanker"], export_gross_202506_Mt=j and j["export_tanker"] / 1e6,
                import_202506_Mt=j and j["import_tanker"] / 1e6,
                net_202506_Mt=j and (j["export_tanker"] - j["import_tanker"]) / 1e6,
                calls_20260228=d.get("2026-02-28", {}).get("portcalls_tanker"))


# ------------------------------------------------------------ docs (optional, polite)
def fetch_docs(out_dir):
    res = {}
    rp = urllib.robotparser.RobotFileParser()
    try:
        with urllib.request.urlopen(urllib.request.Request("https://www.arcgis.com/robots.txt",
                                                           headers={"User-Agent": UA}), timeout=60) as r:
            rp.parse(r.read().decode("utf-8", "replace").splitlines())
    except urllib.error.HTTPError as e:
        rp.parse([] if 400 <= e.code < 500 else ["User-agent: *", "Disallow: /"])
    os.makedirs(os.path.join(out_dir, "docs"), exist_ok=True)
    for layer, item in ITEMS.items():
        url = f"https://www.arcgis.com/sharing/rest/content/items/{item}?f=json"
        if not rp.can_fetch(UA, url):
            res[layer] = dict(url=url, error="robots.txt disallows"); continue
        body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read()
        p = os.path.join(out_dir, "docs", f"item_{item}.json")
        open(p, "wb").write(body)
        desc = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html.unescape(json.loads(body).get("description") or "")))
        desc = desc.replace("\u2019", "'")
        found = {s: (s.replace("\u2019", "'") in desc) for s in DOC_STRINGS[layer]}
        res[layer] = dict(url=url, retrieved_at_utc=now(), sha256=hashlib.sha256(body).hexdigest(), bytes=len(body),
                          strings_found=found, cites_WP21_225="2021/225" in desc,
                          cites_WP25_93=("2025/093" in desc or "25/93" in desc or "Nowcasting Global Trade" in desc))
        time.sleep(6)
    return res


# ------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw", default=os.path.join(HERE, "..", "data", "raw"))
    ap.add_argument("--out", default=os.path.join(HERE, "out"))
    ap.add_argument("--fetch-docs", action="store_true", help="fetch the 2 ArcGIS item descriptions (2 requests)")
    ap.add_argument("--compare", action="append", default=[], help="LABEL=RAW_DIR of another release, repeatable")
    ap.add_argument("--perm-draws", type=int, default=10000)
    a = ap.parse_args()
    raw, out = os.path.abspath(a.raw), os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    started = now()
    data = core.load_raw(raw)
    sets, by = core.port_sets(data["ports"])
    ins = sets["audit_45"]
    end = core.data_end(data["pm"])
    end_ym = int(end[:4]) * 100 + int(end[5:7])
    checks, meas = [], {}

    # --- 1. capacity-field meaning
    li = {}
    for layer in ITEMS:
        p = os.path.join(raw, f"layerinfo_{layer}.json")
        if os.path.exists(p):
            j = json.load(open(p))
            li[layer] = dict(lastEditDate_utc=dt.datetime.fromtimestamp(j["editingInfo"]["lastEditDate"] / 1000,
                             dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
                             fields={f["name"]: dict(type=f["type"], alias=f.get("alias"), description=f.get("description"))
                                     for f in j["fields"]})
    need = {"Daily_Chokepoints_Data": ["capacity_tanker", "n_tanker"],
            "Daily_Ports_Data": ["export_tanker", "import_tanker", "portcalls_tanker"]}
    if len(li) == 2:
        obs = {l: {f: li[l]["fields"].get(f) for f in fs} for l, fs in need.items()}
        ok = all(v and v["type"] == "esriFieldTypeInteger" for l in obs for v in obs[l].values())
        nodesc = all(v and not v["description"] for l in obs for v in obs[l].values())
        checks.append(check("capacity_field_schema", "Do the summed fields exist as integer fields in the layer schema?",
                            "all 5 fields present, esriFieldTypeInteger", dict(fields=obs, layer_schema_has_no_field_descriptions=nodesc),
                            "PASS" if ok else "FAIL"))
    else:
        checks.append(check("capacity_field_schema", "Do the summed fields exist?", "layerinfo present", "layerinfo files missing", "UNKNOWN"))
    earlier = ("audit01-hormuz/verification/2026-10-07/REPORT.md (Q1) and SOURCES.md: ArcGIS item descriptions "
               "3da2b9ca... sha256 08e00ca6..., 83b1bbc7... sha256 c47b7e00...; IMF WP/25/93 Annex II eq. A2.1, "
               "sha256 28ec6524...; WP/21/225 sha256 e5e07052...")
    if a.fetch_docs:
        docs = fetch_docs(out)
        allfound = all(all(v.get("strings_found", {}).values()) and v.get("strings_found") for v in docs.values())
        checks.append(check("capacity_field_definition", "What does PortWatch say capacity_tanker / export_tanker / import_tanker measure?",
                            "item descriptions define them as model-estimated cargo in metric tons (payload share x DWT), not DWT",
                            docs, "PASS" if allfound else "FAIL", earlier))
        meas["documentation_inconsistency"] = {l: dict(cites_WP21_225=v.get("cites_WP21_225"), cites_WP25_93=v.get("cites_WP25_93"))
                                               for l, v in docs.items()}
    else:
        checks.append(check("capacity_field_definition", "What does PortWatch say the fields measure?",
                            "item descriptions define them as estimated cargo in metric tons, not DWT",
                            "not fetched in this run (use --fetch-docs)", "UNKNOWN", earlier))
    checks.append(check("ballast_zeroing_applied_to_series", "Are tanker transits in ballast set to zero in the published chokepoint series?",
                        "WP/25/93 eq. A2.1 (2025 method) is applied to chokepoint6",
                        "documented in WP/25/93 and the PortWatch 2025 changelog; per-vessel data needed to observe it are not public",
                        "UNKNOWN", earlier))

    # --- 2. units
    num_fields = [("pm", f) for f in ("export_tanker", "import_tanker", "portcalls_tanker", "n_days")] + \
                 [("ch", f) for f in ("capacity_tanker", "n_tanker")] + [("bpd", f) for f in ("export_tanker", "import_tanker", "portcalls_tanker")]
    bad = {f"{s}.{f}": sum(1 for r in data[s] if not (isinstance(r[f], int) and r[f] >= 0)) for s, f in num_fields}
    checks.append(check("units_integer_tonnes", "Are all tonnage/count values non-negative integers (t, counts)?",
                        "0 non-integer or negative values", bad, "PASS" if not any(bad.values()) else "FAIL"))
    bpm = {r["ym"]: r for r in data["pm"] if r["portid"] == core.BP}
    dsum = {}
    for r in data["bpd"]:
        k = int(r["date"][:4]) * 100 + int(r["date"][5:7])
        dsum.setdefault(k, [0, 0, 0])
        dsum[k][0] += r["export_tanker"]; dsum[k][1] += r["import_tanker"]; dsum[k][2] += r["portcalls_tanker"]
    mism = [m for m, v in dsum.items() if m in bpm and v != [bpm[m]["export_tanker"], bpm[m]["import_tanker"], bpm[m]["portcalls_tanker"]]]
    checks.append(check("aggregation_consistency_port105", "Do server-side monthly sums equal the sum of daily rows (port105)?",
                        "0 mismatching months", dict(months_compared=len([m for m in dsum if m in bpm]), mismatching=mism),
                        "PASS" if dsum and not mism else ("UNKNOWN" if not dsum else "FAIL")))

    # --- 3. key numbers, both windows
    kn_a = key_numbers(data, AUDIT_START)
    kn_d = key_numbers(data, DIRECTIVE_START)
    bp = port105_facts(data)
    meas["window_audit_2026-03-01"] = kn_a
    meas["window_directive_2025-03-01"] = kn_d
    meas["port105_facts"] = bp
    april = core.balance(data, ins, 202604)["L_t"] / 1e6
    obs = {"net_45_ports_Mt": kn_a["net_Mt"], "C_Mt": kn_a["C_Mt"], "gap_Mt": kn_a["gap_Mt"], "ratio": kn_a["ratio"],
           "baseline_rho_max": kn_a["baseline_rho_max"], "baseline_months": kn_a["baseline_months"],
           "port105_202506_calls": bp["calls_202506"], "port105_202506_export_gross_Mt": bp["export_gross_202506_Mt"],
           "port105_median_calls_2019_2024": bp["median_calls_2019_2024"], "port105_20260228_calls": bp["calls_20260228"],
           "port105_net_window_Mt": kn_a["port105_net_Mt"], "port105_share_of_gap_pct": kn_a["port105_share_of_gap_pct"],
           "gap_excl_port105_Mt": kn_a["gap_excl_port105_Mt"], "gap_excl_Iran_Mt": kn_a["gap_excl_Iran_Mt"],
           "gap_from_April_Mt": april}
    if isinstance(kn_a["burst_days"], dict):
        g = [v["gap_without_Mt"] for v in kn_a["burst_days"].values()]
        dd = [v["days"] for v in kn_a["burst_days"].values()]
        obs.update(burst_gap_min_Mt=min(g), burst_gap_max_Mt=max(g), burst_days_min=min(dd), burst_days_max=max(dd),
                   range_low_Mt=kn_a["range_Mt"][0], range_high_Mt=kn_a["range_Mt"][1])
    claim_rows = {}
    for k, (pub, nd) in PUBLISHED.items():
        v = obs.get(k)
        st = "UNKNOWN" if v is None else ("PASS" if round(v, nd) == round(pub, nd) else "FAIL")
        claim_rows[k] = dict(published=pub, recomputed=v, decimals=nd, status=st)
    checks.append(check("published_numbers_reproduce", "Do the published thread numbers follow from the raw inputs with t -> Mt = /1e6 and the stated rounding?",
                        "every published value equals the recomputed value rounded to the published decimals",
                        claim_rows, "PASS" if all(r["status"] == "PASS" for r in claim_rows.values()) else
                        ("FAIL" if any(r["status"] == "FAIL" for r in claim_rows.values()) else "UNKNOWN"),
                        "42.8 Mt is gross export_tanker; net for June 2025 is reported in measurements.port105_facts"))

    # --- 4. duplicates
    du = core.duplicates(data)
    checks.append(check("duplicate_keys", "Any duplicate port-month keys, chokepoint dates, port105 dates or identical port-month rows?",
                        "all counts 0", du, "PASS" if not any(du.values()) else "FAIL"))
    checks.append(check("duplicate_vessel_events", "Are individual vessel port calls / transits double-counted?",
                        "no duplicated vessel events", "public layers are daily aggregates without vessel identifiers; "
                        "port105 burst days (see measurements) are consistent with, but do not prove, duplicated or spoofed events",
                        "UNKNOWN"))

    # --- 5. gaps
    gp = core.gaps(data, ins, end)
    win_zero = [d for d in gp["chokepoint_zero_tanker_days"] if d >= "2026-03-01"]
    summ = dict(chokepoint_missing_dates=len(gp["chokepoint_missing_dates"]), port_months_absent=len(gp["port_months_absent"]),
                port_months_short=len(gp["port_months_short"]), examples_short=gp["port_months_short"][:10],
                chokepoint_zero_tanker_days_total=len(gp["chokepoint_zero_tanker_days"]),
                chokepoint_zero_tanker_days_in_audit_window=win_zero)
    checks.append(check("row_completeness", "Are daily rows missing (chokepoint6 dates; port-months with fewer rows than days)?",
                        "0 missing chokepoint dates, 0 absent or short port-months for the 45 ports", summ,
                        "PASS" if not (summ["chokepoint_missing_dates"] or summ["port_months_absent"] or summ["port_months_short"]) else "FAIL"))
    checks.append(check("ais_signal_gaps", "Are there AIS reception gaps inside the rows (days with real traffic recorded as 0)?",
                        "no AIS gaps", "a zero row cannot be told apart from a day without traffic in aggregated data; "
                        f"chokepoint6 zero-tanker days in the audit window: {len(win_zero)}", "UNKNOWN"))

    # --- 6. revisions
    def fingerprint(d):
        """SHA-256 over canonical records of the data pages (stable across byte-level serialization changes)."""
        h = hashlib.sha256()
        for f in sorted(os.listdir(d)):
            if f.endswith(".json") and not f.startswith("layerinfo_") and os.path.isfile(os.path.join(d, f)):
                with open(os.path.join(d, f)) as fh:
                    recs = json.load(fh).get("features")
                h.update(f"{f} ".encode() + hashlib.sha256(json.dumps(recs, sort_keys=True, separators=(",", ":")).encode()).digest())
        return h.hexdigest()
    rev = {"primary": dict(inputs_fingerprint=fingerprint(raw), lastEdit={l: v["lastEditDate_utc"] for l, v in li.items()},
                           gap_Mt=kn_a["gap_Mt"], net_Mt=kn_a["net_Mt"], C_Mt=kn_a["C_Mt"],
                           gap_excl_port105_Mt=kn_a["gap_excl_port105_Mt"], gap_excl_Iran_Mt=kn_a["gap_excl_Iran_Mt"],
                           port105_net_Mt=kn_a["port105_net_Mt"], directive_gap_Mt=kn_d["gap_Mt"])}
    for spec in a.compare:
        lab, d = spec.split("=", 1)
        try:
            dd = core.load_raw(d)
            k2, k2d = key_numbers(dd, AUDIT_START), key_numbers(dd, DIRECTIVE_START)
            le = {}
            for layer in ITEMS:
                p = os.path.join(d, f"layerinfo_{layer}.json")
                if os.path.exists(p):
                    le[layer] = dt.datetime.fromtimestamp(json.load(open(p))["editingInfo"]["lastEditDate"] / 1000,
                                                          dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
            rev[lab] = dict(inputs_fingerprint=fingerprint(d), lastEdit=le, n_ports_with_rows=len({r["portid"] for r in dd["pm"]} & ins),
                            dup=core.duplicates(dd), gap_Mt=k2["gap_Mt"], net_Mt=k2["net_Mt"], C_Mt=k2["C_Mt"],
                            gap_excl_port105_Mt=k2["gap_excl_port105_Mt"], gap_excl_Iran_Mt=k2["gap_excl_Iran_Mt"],
                            port105_net_Mt=k2["port105_net_Mt"], directive_gap_Mt=k2d["gap_Mt"])
        except Exception as e:
            rev[lab] = dict(error=f"{type(e).__name__}: {e}")
    comps = [v for k, v in rev.items() if k != "primary" and "gap_Mt" in v and v["n_ports_with_rows"] == len(ins) and not any(v["dup"].values())]
    if comps:
        md_ = max(abs(v["gap_Mt"] - kn_a["gap_Mt"]) for v in comps)
        st = "PASS" if md_ < 0.05 else "FAIL"
        obs_rev = dict(releases=rev, max_abs_gap_delta_Mt=md_)
    else:
        st, obs_rev = "UNKNOWN", dict(releases=rev, note="no complete comparison release supplied")
    checks.append(check("revision_sensitivity", "How much do weekly PortWatch revisions move the audit-window gap?",
                        "|delta gap| < 0.05 Mt between complete releases", obs_rev, st))

    # --- 7. denominator choice
    end_C, end_N, _ = core.monthly_C(data["ch"], end)
    E, I, K = core.monthly_ports(data["pm"], ins)
    base_ms = core.ym_range(201901, 202602)
    win_ms = core.ym_range(AUDIT_START, end_ym)
    def ratio_over(ms, num, den):
        n, d = sum(num(m) for m in ms), sum(den(m) for m in ms)
        return n / d if d else None
    alt = {
        "net_over_C (audit)": (lambda m: E.get(m, 0) - I.get(m, 0), lambda m: end_C.get(m, 0)),
        "gross_export_over_C": (lambda m: E.get(m, 0), lambda m: end_C.get(m, 0)),
        "tanker_calls_over_tanker_transits (unit-free)": (lambda m: K.get(m, 0), lambda m: end_N.get(m, 0)),
    }
    den = {}
    for name, (nu, de) in alt.items():
        bm = [ratio_over([m], nu, de) for m in base_ms if de(m)]
        den[name] = dict(window=ratio_over(win_ms, nu, de), baseline_monthly_max=max(bm), baseline_monthly_median=core.median(bm),
                         window_exceeds_baseline_max=ratio_over(win_ms, nu, de) > max(bm))
    cpt = {m: end_C[m] / end_N[m] for m in end_C if end_N.get(m)}
    den["C_per_transit_t"] = dict(baseline_median=core.median([cpt[m] for m in base_ms if m in cpt]),
                                  window_months={str(m): round(cpt[m]) for m in win_ms if m in cpt})
    robust = den["net_over_C (audit)"]["window_exceeds_baseline_max"] and den["tanker_calls_over_tanker_transits (unit-free)"]["window_exceeds_baseline_max"]
    checks.append(check("denominator_choice", "Does the anomaly survive a unit-free denominator (counts instead of tonnes)?",
                        "window ratio exceeds the pre-crisis monthly maximum under both the tonnage and the count definition",
                        den, "PASS" if robust else "FAIL",
                        "C has no direction split in the public layer; both directions are summed (conservative for L)"))

    # --- 8. falsification: port sets and windows
    ps = {}
    for name, s in sets.items():
        b = core.balance(data, s, AUDIT_START)
        bd = core.balance(data, s, DIRECTIVE_START)
        ps[name] = dict(n_ports=len(s), audit_window_gap_Mt=b["L_t"] / 1e6, directive_window_gap_Mt=bd["L_t"] / 1e6)
    meas["box_rule_equals_audit_rule"] = sets["box_rule"] == ins
    honest = {k: v for k, v in ps.items() if "adversarial" not in k}
    checks.append(check("falsify_port_sets", "Does the audit-window gap stay > 0 under alternative inside-Gulf port sets?",
                        "L > 0 for every alternative set (excluding the deliberately wrong Gulf-of-Oman set)", ps,
                        "PASS" if all(v["audit_window_gap_Mt"] > 0 for v in honest.values()) else "FAIL"))
    starts = core.ym_range(202503, end_ym)
    ws = {}
    for s in starts:
        b = core.balance(data, ins, s); bx = core.balance(data, sets["excl_port105"], s)
        ws[str(s)] = dict(gap_Mt=round(b["L_t"] / 1e6, 4), gap_excl_port105_Mt=round(bx["L_t"] / 1e6, 4), ratio=round(b["ratio"], 4))
    checks.append(check("falsify_windows", "Does the gap stay > 0 for every window start from 2025-03 to the last month (end fixed at data end)?",
                        "L > 0 for all start months", ws, "PASS" if all(v["gap_Mt"] > 0 for v in ws.values()) else "FAIL",
                        "a FAIL here means the sign of L depends on the window; the published thread reports -1.9 Mt from April"))

    # --- 9. negative controls
    nc = {}
    for label, b0, b1 in (("pre_audit_window 2019-01..2026-02", 201901, 202602), ("pre_directive_window 2019-01..2025-02", 201901, 202502)):
        ms = core.ym_range(b0, b1)
        worst = None
        for i in range(len(ms) - 6):
            r = ratio_over(ms[i:i + 7], lambda m: E.get(m, 0) - I.get(m, 0), lambda m: end_C.get(m, 0))
            if worst is None or r > worst[1]:
                worst = (f"{ms[i]}..{ms[i + 6]}", r)
        nc[label] = dict(windows_7_months=len(ms) - 6, max_ratio=worst[1], max_window=worst[0])
    checks.append(check("negative_control_pre_crisis_windows", "In pre-crisis 7-month windows, is (E-I)/C <= 1, as cargo conservation with full visibility requires?",
                        "max ratio <= 1 in every pre-crisis 7-month window", nc,
                        "PASS" if all(v["max_ratio"] <= 1 for v in nc.values()) else "FAIL"))
    loo = core.leave_one_out(data, ins, AUDIT_START)
    rank = [p for p, _ in loo].index(core.BP) + 1
    checks.append(check("negative_control_leave_one_port_out", "Is the gap reduction from dropping port105 specific to it (vs dropping any other port)?",
                        "port105 has the largest reduction of all 45 ports", dict(port105_rank=rank, top5=[(p, by[p]["portname"], round(v, 4)) for p, v in loo[:5]]),
                        "PASS" if rank == 1 else "FAIL"))
    # added after observing the absolute leave-one-out result (post hoc; reported as such)
    exc = []
    for p in sorted(ins):
        rows = {r["ym"]: r["export_tanker"] - r["import_tanker"] for r in data["pm"] if r["portid"] == p}
        med_p = core.median([rows.get(m, 0) for m in core.ym_range(201901, 202412)]) or 0
        exc.append((p, sum(rows.get(m, 0) for m in core.ym_range(AUDIT_START, end_ym)) / 1e6 - len(core.ym_range(AUDIT_START, end_ym)) * med_p / 1e6))
    exc.sort(key=lambda x: -x[1])
    rank_e = [p for p, _ in exc].index(core.BP) + 1
    checks.append(check("negative_control_excess_over_own_baseline", "Ranked by window net export minus the port's own 2019-2024 median month x 7, is port105 the most anomalous port? (post hoc, added after the absolute leave-one-out result)",
                        "port105 ranks 1 of 45", dict(port105_rank=rank_e, top5=[(p, by[p]["portname"], round(v, 4)) for p, v in exc[:5]]),
                        "PASS" if rank_e == 1 else "FAIL"))
    # monthly decomposition of L (audit window)
    mon = {str(m): round((E.get(m, 0) - I.get(m, 0) - end_C.get(m, 0)) / 1e6, 4) for m in win_ms}
    meas["monthly_gap_audit_window_Mt"] = mon
    top_m = max(mon, key=mon.get)
    checks.append(check("gap_not_single_month", "Is the audit-window gap spread over the window rather than produced by one month?",
                        "no single month contributes more than 50% of L",
                        dict(monthly_gap_Mt=mon, largest_month=top_m, largest_share_pct=100 * mon[top_m] / kn_a["gap_Mt"]),
                        "PASS" if mon[top_m] <= 0.5 * kn_a["gap_Mt"] else "FAIL",
                        "hypothesis (not tested here): March 2026 exports dated at port entry while transits collapsed, i.e. cargo loaded but still afloat inside the Gulf"))
    perm = core.permutation_port105(data, core.ym_range(AUDIT_START, end_ym), core.ym_range(201901, 202602), n=a.perm_draws)
    checks.append(check("negative_control_shuffled_terminal", "Is port105's audit-window net export unusual relative to random draws of its own pre-crisis months?",
                        "P(random 7 pre-crisis months >= observed) < 0.05", perm, "PASS" if perm["p_random_months"] < 0.05 else "FAIL",
                        "contiguous-block count shows whether earlier bursts (e.g. 2025) reached the same size"))

    # --- write
    finished = now()
    status_counts = {s: sum(c["status"] == s for c in checks) for s in ("PASS", "FAIL", "UNKNOWN")}
    results = dict(schema="audit01-forensic-results/1", started_utc=started, finished_utc=finished, data_end=end,
                   status_counts=status_counts, checks=checks, measurements=meas,
                   note="All values are PortWatch model estimates. PASS/FAIL refer only to the stated hypothesis on the observed inputs.")
    rp = os.path.join(out, "results.json")
    json.dump(results, open(rp, "w"), indent=1, default=str)

    prov = {}
    pp = os.path.join(os.path.dirname(raw), "provenance.jsonl")
    if os.path.exists(pp):
        for line in open(pp):
            r = json.loads(line); prov[r["name"]] = r
    inputs = []
    for f in sorted(os.listdir(raw)):
        p = os.path.join(raw, f)
        if os.path.isfile(p):
            h = sha(p); pr = prov.get(f, {})
            try:
                with open(p) as fh:
                    j = json.load(fh)
                recs = j.get("features", j.get("fields"))
                rh = hashlib.sha256(json.dumps(recs, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            except Exception:
                rh = None
            inputs.append(dict(name=f, bytes=os.path.getsize(p), sha256=h, records_sha256=rh, url=pr.get("url"),
                               retrieved_at_utc=pr.get("retrieved_at_utc"), provenance_sha256_match=(pr.get("sha256") == h) if pr else None))
    deps = {}
    for pkg in ("pandas", "numpy", "matplotlib"):
        try:
            deps[pkg] = md.version(pkg)
        except md.PackageNotFoundError:
            deps[pkg] = None
    code_files = sorted(os.path.join(dp, f) for dp, _, fs in os.walk(HERE) for f in fs
                        if f.endswith(".py") and "out" not in os.path.relpath(dp, HERE).split(os.sep))
    manifest = dict(schema="audit01-forensic-manifest/1", created_utc=finished,
                    command=" ".join([os.path.basename(sys.executable)] + sys.argv),
                    code=dict(git_head=git("rev-parse", "HEAD"), git_dirty=bool(git("status", "--porcelain", "--", "."))
                              if git("rev-parse", "HEAD") else None,
                              files={os.path.relpath(p, os.path.dirname(HERE)): sha(p) for p in code_files}),
                    dependencies=dict(python=sys.version.split()[0], implementation=platform.python_implementation(),
                                      platform=platform.platform(), forensic_requires="stdlib only",
                                      pipeline_packages_installed=deps),
                    portwatch_release=rev["primary"]["lastEdit"], inputs=inputs,
                    outputs={"results.json": sha(rp)}, status_counts=status_counts)
    docs_dir = os.path.join(out, "docs")
    if os.path.isdir(docs_dir):
        for f in sorted(os.listdir(docs_dir)):
            manifest["outputs"][f"docs/{f}"] = sha(os.path.join(docs_dir, f))
    mp = os.path.join(out, "manifest.json")
    json.dump(manifest, open(mp, "w"), indent=1)
    with open(os.path.join(out, "SHA256SUMS"), "w") as fh:
        for f in ["results.json", "manifest.json"] + [f"docs/{x}" for x in (sorted(os.listdir(docs_dir)) if os.path.isdir(docs_dir) else [])]:
            fh.write(f"{sha(os.path.join(out, f))}  {f}\n")
    print(json.dumps(dict(status_counts=status_counts, checks={c["id"]: c["status"] for c in checks},
                          audit_window_gap_Mt=round(kn_a["gap_Mt"], 4), directive_window_gap_Mt=round(kn_d["gap_Mt"], 4),
                          results_sha256=sha(rp), manifest_sha256=sha(mp)), indent=1))


if __name__ == "__main__":
    main()
