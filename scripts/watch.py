#!/usr/bin/env python3
"""watch.py - daily check of the IMF PortWatch Daily Chokepoints Data for the Strait of Hormuz (chokepoint6).

Writes a compact snapshot to data/watch/portwatch_hormuz.json (latest date, latest values, last 28 days,
per-year hashes, sha256 of the raw response). Source data is not redistributed beyond these few values.
Outputs for GitHub Actions (via $GITHUB_OUTPUT): changed, notable, failure_issue, and a summary file.
Network or API failures exit 0 with a warning; after 3 consecutive failures it asks for one issue.
Standard library only.
"""
import datetime as dt, hashlib, json, os, sys, time, urllib.parse, urllib.request

B = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
LAYER = f"{B}/Daily_Chokepoints_Data/FeatureServer/0"
FIELDS = ["n_tanker", "capacity_tanker", "n_total", "capacity"]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SNAP = os.path.join(ROOT, "data", "watch", "portwatch_hormuz.json")
STATUS = os.path.join(ROOT, "data", "watch", "status.json")
SUMMARY = os.path.join(ROOT, "data", "watch", ".summary.md")  # not committed (gitignored)
RECENT = 28


def get(url, tries=3):
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "open-data-audits-watch/1.0"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            if i == tries - 1:
                raise
            print(f"retry {i + 1}: {e}", file=sys.stderr)
            time.sleep(10 * (i + 1))


def fetch_series():
    raw, rows, off = [], [], 0
    while True:
        p = {"f": "json", "returnGeometry": "false", "where": "portid='chokepoint6'",
             "outFields": "date," + ",".join(FIELDS), "orderByFields": "date",
             "resultOffset": off, "resultRecordCount": 1000}
        body = get(f"{LAYER}/query?" + urllib.parse.urlencode(p))
        d = json.loads(body)
        if "error" in d:
            raise RuntimeError(f"API error: {d['error']}")
        feats = d.get("features", [])
        raw.append(body)
        for f in feats:
            a = f["attributes"]
            date = a["date"]
            if isinstance(date, (int, float)):  # epoch ms fallback
                date = dt.datetime.fromtimestamp(date / 1000, dt.timezone.utc).strftime("%Y-%m-%d")
            rows.append({"date": str(date)[:10], **{k: a.get(k) for k in FIELDS}})
        if not d.get("exceededTransferLimit") and len(feats) < 1000:
            break
        off += 1000
    if not rows:
        raise RuntimeError("empty response")
    rows.sort(key=lambda r: r["date"])
    meta = json.loads(get(f"{LAYER}?f=json"))
    led = (meta.get("editingInfo") or {}).get("dataLastEditDate")
    led = dt.datetime.fromtimestamp(led / 1000, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ") if led else None
    return rows, hashlib.sha256(b"".join(raw)).hexdigest(), led


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
        json.dump(obj, f, indent=1, sort_keys=False)
        f.write("\n")


def out(**kw):
    gh = os.environ.get("GITHUB_OUTPUT")
    for k, v in kw.items():
        print(f"{k}={v}")
        if gh:
            with open(gh, "a") as f:
                f.write(f"{k}={v}\n")


def main():
    now = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    status = load(STATUS, {"consecutive_failures": 0})
    try:
        rows, raw_sha, led = fetch_series()
    except Exception as e:  # noqa: BLE001
        n = status.get("consecutive_failures", 0) + 1
        status.update(consecutive_failures=n, last_failure_utc=now, last_error=str(e)[:300])
        save(STATUS, status)
        print(f"::warning::PortWatch fetch failed ({n} in a row): {e}")
        open(SUMMARY, "w").write(f"PortWatch fetch failed {n} times in a row. Last error: `{str(e)[:300]}`\n")
        out(changed="true", notable="false", failure_issue="true" if n == 3 else "false")
        return
    status_changed = status.get("consecutive_failures", 0) != 0
    status = {"consecutive_failures": 0}

    prev = load(SNAP, None)
    latest = rows[-1]
    snap = {
        "source": "IMF PortWatch, Daily Chokepoints Data, Strait of Hormuz (chokepoint6)",
        "source_url": f"{LAYER}/query",
        "portwatch_data_last_edit_utc": led,
        "checked_at_utc": now,
        "n_days": len(rows),
        "first_date": rows[0]["date"],
        "latest_date": latest["date"],
        "latest": {k: latest[k] for k in FIELDS},
        "raw_sha256": raw_sha,
        "series_sha256": h(rows),
        "year_sha256": year_hashes(rows),
        "recent_days": rows[-RECENT:],
    }
    lines, notable = [], False
    if prev is None:
        lines.append(f"First snapshot: {len(rows)} days, {rows[0]['date']} to {latest['date']}.")
        changed = True
    else:
        changed = prev.get("series_sha256") != snap["series_sha256"] or prev.get("raw_sha256") != raw_sha
        pl = prev.get("latest_date", "")
        new = [r for r in rows if r["date"] > pl]
        if new:
            notable = True
            lines.append(f"**New data**: {len(new)} new day(s), {new[0]['date']} to {new[-1]['date']} "
                         f"(previous latest: {pl}).")
            lines.append(f"Latest day {latest['date']}: " + ", ".join(f"{k}={latest[k]}" for k in FIELDS) + ".")
        old = [r for r in rows if r["date"] <= pl]
        if h(old) != prev.get("series_sha256"):
            notable = True
            lines.append("**Revision**: values for already-published days changed.")
            pyh, nyh = prev.get("year_sha256", {}), year_hashes(old)
            ys = sorted(y for y in set(pyh) | set(nyh) if pyh.get(y) != nyh.get(y))
            lines.append("Years affected: " + (", ".join(ys) or "n/a") + ".")
            pr = {r["date"]: r for r in prev.get("recent_days", [])}
            cur = {r["date"]: r for r in old}
            diffs = [f"| {d} | " + " | ".join(f"{pr[d][k]} → {cur[d][k]}" if pr[d][k] != cur.get(d, {}).get(k)
                                               else str(pr[d][k]) for k in FIELDS) + " |"
                     for d in sorted(pr) if pr[d] != cur.get(d)]
            if diffs:
                lines += ["", "| date | " + " | ".join(FIELDS) + " |", "|---" * (len(FIELDS) + 1) + "|"] + diffs[:40]
        if changed and not notable:
            lines.append("Raw response changed (formatting/metadata), no new days and no revised values.")
        if not changed:
            snap["checked_at_utc"] = prev.get("checked_at_utc", now)  # keep file stable: no commit when nothing changed
    save(SNAP, snap)
    save(STATUS, status)
    open(SUMMARY, "w").write("\n".join(lines) + f"\n\nPortWatch data last edit: {led}. Checked: {now}.\n")
    print("\n".join(lines) or "No change.")
    out(changed=str(changed or status_changed).lower(), notable=str(notable).lower(), failure_issue="false")


if __name__ == "__main__":
    main()
