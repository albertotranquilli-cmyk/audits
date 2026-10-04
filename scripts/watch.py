#!/usr/bin/env python3
"""watch.py - scheduled checks of free official data sources. Standard library only.

Sources: IMF PortWatch Strait of Hormuz daily transits; JODI Oil World Database, China crude (production,
imports, exports, refinery intake, kb/d); EIA weekly US commercial crude stocks excl. SPR (WCESTUS1).
Each source gets a compact snapshot in data/watch/<id>.json (latest period and values, recent periods,
per-year hashes, sha256 of the raw response). Only a few summary values are kept; source data is not
redistributed. A source is "notable" when a new period appears or already-published values are revised.
On notable changes the source URLs are saved to the Wayback Machine (rate-limited, failures non-fatal),
and OpenTimestamps proofs are created/upgraded (scripts/stamp.py).
Outputs for GitHub Actions ($GITHUB_OUTPUT): changed, notable, failure_issue; summary in data/watch/.summary.md.
A source failure never fails the run; one issue is requested when a source fails 3 runs in a row.
"""
import csv, datetime as dt, hashlib, io, json, os, re, sys, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WATCH = os.path.join(ROOT, "data", "watch")
STATUS = os.path.join(WATCH, "status.json")
SUMMARY = os.path.join(WATCH, ".summary.md")  # gitignored
UA = "open-data-audits-watch/1.1 (+https://github.com/albertotranquilli-cmyk/audits)"


def get(url, tries=3, timeout=90):
    for i in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) == 404 or i == tries - 1:
                raise
            print(f"retry {i + 1} {url[:80]}: {e}", file=sys.stderr)
            time.sleep(10 * (i + 1))


def utc(ms):
    return dt.datetime.fromtimestamp(ms / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if ms else None


# ---------------------------------------------------------------- sources
PW = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0"
PW_F = ["n_tanker", "capacity_tanker", "n_total", "capacity"]


def portwatch():
    raw, rows, off, urls = [], [], 0, []
    while True:
        p = {"f": "json", "returnGeometry": "false", "where": "portid='chokepoint6'",
             "outFields": "date," + ",".join(PW_F), "orderByFields": "date",
             "resultOffset": off, "resultRecordCount": 1000}
        url = f"{PW}/query?" + urllib.parse.urlencode(p)
        urls.append(url)
        body = get(url)
        d = json.loads(body)
        if "error" in d:
            raise RuntimeError(f"API error: {d['error']}")
        feats = d.get("features", [])
        raw.append(body)
        for f in feats:
            a = f["attributes"]
            date = utc(a["date"])[:10] if isinstance(a["date"], (int, float)) else str(a["date"])[:10]
            rows.append({"date": date, **{k: a.get(k) for k in PW_F}})
        if not d.get("exceededTransferLimit") and len(feats) < 1000:
            break
        off += 1000
    meta = json.loads(get(f"{PW}?f=json"))
    led = utc((meta.get("editingInfo") or {}).get("dataLastEditDate"))
    return rows, raw, led, [f"{PW}?f=json", urls[0]]


JODI = "https://www.jodidata.org/_resources/files/downloads/oil-data/annual-csv/primary/"
JODI_F = {"INDPROD": "production", "TOTIMPSB": "imports", "TOTEXPSB": "exports", "REFINOBS": "refinery_intake"}


def jodi_china():
    y0 = dt.datetime.now(dt.timezone.utc).year
    raw, rows, urls = [], {}, []
    for y in (y0 - 1, y0):
        body = None
        for name in (f"primaryyear{y}.csv", f"{y}.csv"):
            try:
                body = get(JODI + name, timeout=180)
                urls.append(JODI + name)
                break
            except Exception as e:  # noqa: BLE001
                if getattr(e, "code", None) != 404:
                    raise
        if body is None:
            continue
        raw.append(body)
        for r in csv.DictReader(io.StringIO(body.decode("utf-8-sig", "replace"))):
            if r["REF_AREA"] == "CN" and r["ENERGY_PRODUCT"] == "CRUDEOIL" and r["UNIT_MEASURE"] == "KBD" \
                    and r["FLOW_BREAKDOWN"] in JODI_F:
                v = r["OBS_VALUE"].strip()
                try:
                    v = float(v)
                except ValueError:
                    continue  # "-", "x": not reported
                rows.setdefault(r["TIME_PERIOD"], {"date": r["TIME_PERIOD"]})[JODI_F[r["FLOW_BREAKDOWN"]]] = v
    if not raw:
        raise RuntimeError("no JODI file found")
    out = [{"date": d, **{k: rows[d].get(k) for k in JODI_F.values()}} for d in sorted(rows)]
    return out, raw, None, urls


EIA = "https://www.eia.gov/dnav/pet/hist/LeafHandler.ashx?n=PET&s=WCESTUS1&f=W"
MON = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}


def eia_stocks():
    body = get(EIA)
    s = body.decode("utf-8", "replace")
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", s, re.S):
        lab = re.search(r"class='B6'>(?:&nbsp;)*\s*(\d{4})-(\w{3})", tr)
        if not lab:
            continue
        year = int(lab.group(1))
        for md, val in re.findall(r"class='B5'>(\d\d/\d\d)&nbsp;</td>\s*<td class='B3'>([\d,]+)", tr):
            m, d = map(int, md.split("/"))
            yy = year - 1 if (MON[lab.group(2)] == 1 and m == 12) else year
            rows.append({"date": f"{yy:04d}-{m:02d}-{d:02d}", "stocks_kbbl": int(val.replace(",", ""))})
    if len(rows) < 100:
        raise RuntimeError(f"EIA page parse failed ({len(rows)} rows)")
    rel = re.search(r"Release Date:\s*([\d/]+)", s)
    return sorted(rows, key=lambda r: r["date"]), [body], rel and rel.group(1), [EIA]


SOURCES = [
    {"id": "portwatch_hormuz", "name": "IMF PortWatch, Daily Chokepoints Data, Strait of Hormuz (chokepoint6)",
     "url": f"{PW}/query", "fn": portwatch, "recent": 28},
    {"id": "jodi_china_crude", "name": "JODI Oil World Database, China crude oil, kb/d", "url": JODI,
     "fn": jodi_china, "recent": 6},
    {"id": "eia_us_crude_stocks", "name": "EIA weekly US commercial crude stocks excl. SPR (WCESTUS1), kb",
     "url": EIA, "fn": eia_stocks, "recent": 8},
]


# ---------------------------------------------------------------- helpers
def h(rows):
    return hashlib.sha256(json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def year_hashes(rows):
    ys = {}
    for r in rows:
        ys.setdefault(r["date"][:4], []).append(r)
    return {y: h(v) for y, v in sorted(ys.items())}


def load(p, default):
    try:
        return json.load(open(p))
    except Exception:  # noqa: BLE001
        return default


def save(p, obj):
    with open(p, "w") as f:
        json.dump(obj, f, indent=1)
        f.write("\n")


def out(**kw):
    gh = os.environ.get("GITHUB_OUTPUT")
    for k, v in kw.items():
        print(f"{k}={v}")
        if gh:
            with open(gh, "a") as f:
                f.write(f"{k}={v}\n")


def wayback(urls, pause=30):
    """Save Page Now (anonymous, free): one URL at a time, one retry, failures recorded and non-fatal."""
    res = []
    for i, u in enumerate(urls):
        if i:
            time.sleep(pause)
        for attempt in (0, 1):
            try:
                if attempt:
                    time.sleep(60)
                req = urllib.request.Request("https://web.archive.org/save/" + u, headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=180) as r:
                    loc = r.headers.get("Content-Location") or r.geturl()
                res.append({"url": u, "archive": urllib.parse.urljoin("https://web.archive.org", loc)})
                break
            except Exception as e:  # noqa: BLE001
                if attempt:
                    print(f"::warning::Wayback save failed for {u[:80]}: {e}")
                    res.append({"url": u, "archive": None, "error": str(e)[:120]})
    return res


def compare(prev, rows, fields):
    """Return (notable, lines)."""
    pl = prev.get("latest_date", "")
    lines, notable = [], False
    new = [r for r in rows if r["date"] > pl]
    if new:
        notable = True
        lines.append(f"**New data**: {len(new)} new period(s), {new[0]['date']} to {new[-1]['date']} "
                     f"(previous latest: {pl}).")
        lines.append(f"Latest {rows[-1]['date']}: " + ", ".join(f"{k}={rows[-1][k]}" for k in fields) + ".")
    old = [r for r in rows if r["date"] <= pl]
    pyh, nyh = prev.get("year_sha256", {}), year_hashes(old)
    ys = sorted(y for y in set(pyh) & set(nyh) if pyh[y] != nyh[y])
    if ys:
        notable = True
        lines.append("**Revision**: already-published values changed. Years affected: " + ", ".join(ys) + ".")
        pr = {r["date"]: r for r in prev.get("recent", prev.get("recent_days", []))}
        cur = {r["date"]: r for r in old}
        diffs = [f"| {d} | " + " | ".join(f"{pr[d].get(k)} → {cur.get(d, {}).get(k)}"
                                           if pr[d].get(k) != cur.get(d, {}).get(k) else str(pr[d].get(k))
                                           for k in fields) + " |" for d in sorted(pr) if pr[d] != cur.get(d)]
        if diffs:
            lines += ["", "| period | " + " | ".join(fields) + " |", "|---" * (len(fields) + 1) + "|"] + diffs[:40]
    return notable, lines


# ---------------------------------------------------------------- main
def main():
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = load(STATUS, {})
    if "consecutive_failures" in status:  # v1 format (PortWatch only)
        status = {"portwatch_hormuz": {"consecutive_failures": status["consecutive_failures"]}}
    changed = notable_any = fail_issue = False
    summary = []
    archive_queue = []
    for src in SOURCES:
        sid, path = src["id"], os.path.join(WATCH, src["id"] + ".json")
        st = status.get(sid, {"consecutive_failures": 0})
        try:
            rows, raw, led, urls = src["fn"]()
            rows = [r for r in rows if any(v is not None for k, v in r.items() if k != "date")]
            if not rows:
                raise RuntimeError("no data rows")
        except Exception as e:  # noqa: BLE001
            n = st.get("consecutive_failures", 0) + 1
            status[sid] = {"consecutive_failures": n, "last_failure_utc": now, "last_error": str(e)[:300]}
            changed = True
            fail_issue |= n == 3
            print(f"::warning::{sid} fetch failed ({n} in a row): {e}")
            summary.append(f"## {src['name']}\nFetch failed {n} time(s) in a row. Last error: `{str(e)[:300]}`\n")
            continue
        if st.get("consecutive_failures"):
            changed = True
        status[sid] = {"consecutive_failures": 0}
        fields = [k for k in rows[-1] if k != "date"]
        prev = load(path, None)
        raw_sha = hashlib.sha256(b"".join(raw)).hexdigest()
        snap = {"source": src["name"], "source_url": src["url"], "publisher_last_edit": led,
                "checked_at_utc": now, "n_periods": len(rows), "first_date": rows[0]["date"],
                "latest_date": rows[-1]["date"], "latest": {k: rows[-1][k] for k in fields},
                "raw_sha256": raw_sha, "series_sha256": h(rows), "year_sha256": year_hashes(rows),
                "recent": rows[-src["recent"]:]}
        if prev is None:
            notable, lines = True, [f"First snapshot: {len(rows)} periods, {rows[0]['date']} to {rows[-1]['date']}."]
        else:
            notable, lines = compare(prev, rows, fields)
            if prev.get("series_sha256") == snap["series_sha256"]:
                snap["checked_at_utc"] = prev.get("checked_at_utc", now)
                snap["raw_sha256"] = prev.get("raw_sha256", raw_sha)  # cosmetic response changes ignored
                snap["wayback"] = prev.get("wayback")
            elif not notable:
                lines.append("Values changed outside the compared range (e.g. year coverage); no new or revised "
                             "published values.")
        if snap.get("wayback") is None:
            snap.pop("wayback", None)
        if notable:
            archive_queue.append((snap, urls))
        elif any(not w.get("archive") for w in snap.get("wayback") or []):  # retry failed saves on later runs
            archive_queue.append((snap, None))
            snap["_path"] = path
            changed = True
        if prev is None or prev.get("series_sha256") != snap["series_sha256"] or "recent_days" in prev:
            changed = True
            snap["_path"] = path
        elif "_path" not in snap:
            snap["_path"] = None
        src["snap"] = snap
        if prev is not None and notable:
            notable_any = True
            summary.append(f"## {src['name']}\n" + "\n".join(lines) + f"\n\nPublisher last edit: {led}.\n")
        print(f"{sid}: " + (" ".join(lines) if lines else "no change"))
    if os.environ.get("WATCH_NO_WAYBACK") != "1":
        for snap, urls in archive_queue:
            if urls is None:  # retry only the failed ones
                ok = [w for w in snap["wayback"] if w.get("archive")]
                snap["wayback"] = ok + wayback([w["url"] for w in snap["wayback"] if not w.get("archive")])
            else:
                snap["wayback"] = wayback(urls)
    for src in SOURCES:
        snap = src.get("snap")
        if snap and snap.pop("_path", None):
            save(os.path.join(WATCH, src["id"] + ".json"), snap)
    save(STATUS, status)
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import stamp
        if stamp.run():
            changed = True
    except Exception as e:  # noqa: BLE001
        print(f"::warning::stamping skipped: {e}")
    try:
        import scout  # Mondays (UTC) only, or SCOUT_FORCE=1
        if scout.run():
            changed = True
    except Exception as e:  # noqa: BLE001
        print(f"::warning::scout failed: {e}")
    open(SUMMARY, "w").write(("\n".join(summary) or "No change.") + f"\n\nChecked: {now}.\n")
    out(changed=str(changed).lower(), notable=str(notable_any).lower(), failure_issue=str(fail_issue).lower())


if __name__ == "__main__":
    main()
