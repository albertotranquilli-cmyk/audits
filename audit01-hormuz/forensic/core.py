"""core.py - pure, stdlib-only functions for the AUDIT #1 forensic checks.

Nothing here downloads data or imports scripts/analysis.py. All quantities are PortWatch model estimates in metric
tonnes (t); Mt = t / 1e6. Inputs are the raw ArcGIS JSON pages written by scripts/get_data.py.
"""
import calendar, datetime as dt, glob, json, os, random, statistics

BP = "port105"                      # Bandar-E Pars Terminal
GULF_ISO = ("ARE", "SAU", "QAT", "KWT", "BHR", "IRQ", "IRN", "OMN")


# ---------------------------------------------------------------- loading
def _pages(raw, pattern):
    files = sorted(glob.glob(os.path.join(raw, pattern)))
    rows, per_file = [], {}
    for p in files:
        with open(p) as fh:
            d = json.load(fh)
        if "error" in d:
            raise ValueError(f"API error object in {p}")
        feats = [f["attributes"] for f in d.get("features", [])]
        per_file[os.path.basename(p)] = len(feats)
        rows += feats
    return rows, per_file


def norm_date(v):
    """PortWatch has served `date` both as 'YYYY-MM-DD' and as epoch milliseconds."""
    if isinstance(v, (int, float)):
        return dt.datetime.fromtimestamp(v / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
    return str(v)[:10]


def load_raw(raw):
    ports, _ = _pages(raw, "ports_db_gulf*_p*.json")
    ch, chf = _pages(raw, "chokepoint6_daily*_p*.json")
    pm, pmf = _pages(raw, "ports_monthly_gulf*_p*.json")
    bpd, bpf = _pages(raw, "port105_daily*_p*.json")
    for r in ch + bpd:
        r["date"] = norm_date(r["date"])
    for r in pm:
        r["ym"] = int(r["year"]) * 100 + int(r["month"])
    return dict(ports=ports, ch=ch, pm=pm, bpd=bpd, files=dict(ch=chf, pm=pmf, bpd=bpf))


# ---------------------------------------------------------------- port sets
def inside_audit_rule(p):
    """The audit's rule, restated (scripts/analysis.py, README 'Method' 1)."""
    iso, lat, lon = p["ISO3"], p["lat"], p["lon"]
    if iso in ("KWT", "BHR", "IRQ", "QAT"):
        return True
    if iso == "SAU":
        return lon > 45
    if iso == "ARE":
        return lon < 56.2
    if iso == "IRN":
        return lat < 31 and lon < 56.5
    return False


def inside_box_rule(p):
    """Independent geometric rule: box west of the Strait narrows (45<lon<56.3, 23.5<lat<31.5)."""
    return 45 < p["lon"] < 56.3 and 23.5 < p["lat"] < 31.5


def port_sets(ports):
    by = {p["portid"]: p for p in ports}
    audit = {k for k, p in by.items() if inside_audit_rule(p)}
    box = {k for k, p in by.items() if inside_box_rule(p)}
    near_strait = {k for k in audit if by[k]["lon"] > 55.9}          # within ~50 km of the narrows
    gulf_of_oman = {k for k, p in by.items() if p["ISO3"] in ("ARE", "OMN", "IRN") and 56.2 <= p["lon"] < 60
                    and 23.5 < p["lat"] < 27}                         # Fujairah, Khor Fakkan, Sohar, Jask ...
    return {
        "audit_45": audit,
        "box_rule": box,
        "excl_port105": audit - {BP},
        "excl_Iran": {k for k in audit if by[k]["ISO3"] != "IRN"},
        "excl_UAE": {k for k in audit if by[k]["ISO3"] != "ARE"},
        "excl_near_strait": audit - near_strait,
        "arab_crude_exporters_only": {k for k in audit if by[k]["ISO3"] in ("SAU", "KWT", "IRQ", "QAT", "BHR")},
        "plus_gulf_of_oman_ports(adversarial,wrong side)": audit | gulf_of_oman,
    }, by


# ---------------------------------------------------------------- calendar helpers
def ym_range(a, b):
    out, y, m = [], a // 100, a % 100
    while y * 100 + m <= b:
        out.append(y * 100 + m)
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def days_in(ym):
    return calendar.monthrange(ym // 100, ym % 100)[1]


def data_end(pm):
    last = max(r["ym"] for r in pm)
    nd = max(r["n_days"] for r in pm if r["ym"] == last)
    return f"{last // 100:04d}-{last % 100:02d}-{nd:02d}"


# ---------------------------------------------------------------- mass balance
def monthly_C(ch, end):
    C, N, D = {}, {}, {}
    for r in ch:
        if r["date"] > end:
            continue
        k = int(r["date"][:4]) * 100 + int(r["date"][5:7])
        C[k] = C.get(k, 0) + r["capacity_tanker"]
        N[k] = N.get(k, 0) + r["n_tanker"]
        D[k] = D.get(k, 0) + 1
    return C, N, D


def monthly_ports(pm, portset):
    E, I, K = {}, {}, {}
    for r in pm:
        if r["portid"] in portset:
            k = r["ym"]
            E[k] = E.get(k, 0) + r["export_tanker"]
            I[k] = I.get(k, 0) + r["import_tanker"]
            K[k] = K.get(k, 0) + r["portcalls_tanker"]
    return E, I, K


def balance(data, portset, start_ym, end_ym=None):
    """L = (E - I) - C over calendar months start_ym..end_ym (end = last port month, cut at last port day)."""
    end = data_end(data["pm"])
    end_ym = end_ym or int(end[:4]) * 100 + int(end[5:7])
    C, N, _ = monthly_C(data["ch"], end)
    E, I, K = monthly_ports(data["pm"], portset)
    ms = ym_range(start_ym, end_ym)
    e, i, c = sum(E.get(m, 0) for m in ms), sum(I.get(m, 0) for m in ms), sum(C.get(m, 0) for m in ms)
    return dict(start=start_ym, end=end_ym, E_t=e, I_t=i, net_t=e - i, C_t=c, L_t=e - i - c,
                ratio=(e - i) / c if c else None, calls=sum(K.get(m, 0) for m in ms),
                transits=sum(N.get(m, 0) for m in ms))


def monthly_rho(data, portset, months):
    end = data_end(data["pm"])
    C, _, _ = monthly_C(data["ch"], end)
    E, I, _ = monthly_ports(data["pm"], portset)
    return {m: (E.get(m, 0) - I.get(m, 0)) / C[m] for m in months if C.get(m)}


def burst_days(data, start_date, end_date, k):
    sel = [r for r in data["bpd"] if start_date <= r["date"] <= end_date and r["portcalls_tanker"] >= k]
    return sel, sum(r["export_tanker"] - r["import_tanker"] for r in sel)


def daily_covers(data, start_date, end_date):
    ds = {r["date"] for r in data["bpd"]}
    d0, d1 = dt.date.fromisoformat(start_date), dt.date.fromisoformat(end_date)
    return all((d0 + dt.timedelta(n)).isoformat() in ds for n in range((d1 - d0).days + 1))


# ---------------------------------------------------------------- integrity
def duplicates(data):
    pk = [(r["portid"], r["ym"]) for r in data["pm"]]
    cd = [r["date"] for r in data["ch"]]
    bd = [r["date"] for r in data["bpd"]]
    rows = [json.dumps(r, sort_keys=True) for r in data["pm"]]
    return dict(port_month_dup_keys=len(pk) - len(set(pk)), chokepoint_dup_dates=len(cd) - len(set(cd)),
                port105_dup_dates=len(bd) - len(set(bd)), port_month_identical_rows=len(rows) - len(set(rows)))


def gaps(data, portset, end):
    """Missing daily rows: chokepoint dates, and port-months whose n_days < calendar days."""
    d0 = dt.date.fromisoformat(min(r["date"] for r in data["ch"]))
    d1 = dt.date.fromisoformat(end)
    have = {r["date"] for r in data["ch"]}
    miss_ch = [(d0 + dt.timedelta(n)).isoformat() for n in range((d1 - d0).days + 1)
               if (d0 + dt.timedelta(n)).isoformat() not in have]
    last_ym = int(end[:4]) * 100 + int(end[5:7])
    short, absent = [], []
    first_ym = min(r["ym"] for r in data["pm"])
    for p in sorted(portset):
        rows = {r["ym"]: r for r in data["pm"] if r["portid"] == p}
        for m in ym_range(first_ym, last_ym):
            want = int(end[8:10]) if m == last_ym else days_in(m)
            if m not in rows:
                absent.append((p, m))
            elif rows[m]["n_days"] < want:
                short.append((p, m, rows[m]["n_days"], want))
    zero_ch = [r["date"] for r in data["ch"] if r["date"] <= end and r["n_tanker"] == 0]
    return dict(chokepoint_missing_dates=miss_ch, chokepoint_zero_tanker_days=zero_ch,
                port_months_absent=absent, port_months_short=short)


# ---------------------------------------------------------------- negative controls
def leave_one_out(data, portset, start_ym):
    base = balance(data, portset, start_ym)
    out = []
    for p in sorted(portset):
        b = balance(data, portset - {p}, start_ym)
        out.append((p, (base["L_t"] - b["L_t"]) / 1e6))
    out.sort(key=lambda x: -x[1])
    return out


def permutation_port105(data, window_months, history_months, n=10000, seed=20261007):
    """Random draws of len(window) months from port105's own pre-window history; P(sum >= observed)."""
    net = {r["ym"]: r["export_tanker"] - r["import_tanker"] for r in data["pm"] if r["portid"] == BP}
    obs = sum(net.get(m, 0) for m in window_months)
    hist = [net.get(m, 0) for m in history_months]
    rng = random.Random(seed)
    k = len(window_months)
    ge = sum(1 for _ in range(n) if sum(rng.sample(hist, k)) >= obs)
    blocks = [sum(hist[i:i + k]) for i in range(len(hist) - k + 1)]
    return dict(observed_Mt=obs / 1e6, draws=n, seed=seed, p_random_months=(ge + 1) / (n + 1),
                contiguous_blocks=len(blocks), blocks_ge_observed=sum(b >= obs for b in blocks),
                max_block_Mt=max(blocks) / 1e6 if blocks else None)


def median(xs):
    return statistics.median(xs) if xs else None
