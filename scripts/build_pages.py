#!/usr/bin/env python3
"""build_pages.py - regenerates docs/index.html from data/watch/*.json. Standard library only."""
import glob, html, json, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "https://github.com/albertotranquilli-cmyk/audits"
e = html.escape
rows = []
for p in sorted(glob.glob(os.path.join(ROOT, "data", "watch", "*.json"))):
    name = os.path.basename(p)
    if name == "status.json":
        continue
    s = json.load(open(p))
    latest = ", ".join(f"{k} = {v}" for k, v in (s.get("latest") or {}).items())
    rows.append(f"<tr><td><a href=\"{REPO}/blob/main/data/watch/{e(name)}\">{e(s.get('source', name))}</a></td>"
                f"<td>{e(str(s.get('latest_date')))}</td><td>{e(latest)}</td>"
                f"<td>{e(str(s.get('publisher_last_edit') or s.get('portwatch_data_last_edit_utc')))}</td><td>{e(str(s.get('checked_at_utc')))}</td>"
                f"<td><code>{e(str(s.get('raw_sha256', ''))[:12])}</code></td></tr>")
st = {}
try:
    st = json.load(open(os.path.join(ROOT, "data", "watch", "status.json")))
except Exception:  # noqa: BLE001
    pass
warn = "".join(f"<p><strong>Warning:</strong> {e(k)}: the last {v['consecutive_failures']} fetch attempt(s) failed.</p>"
               for k, v in st.items() if isinstance(v, dict) and v.get("consecutive_failures"))
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Open data audits</title>
<style>body{{font-family:system-ui,sans-serif;max-width:60rem;margin:2rem auto;padding:0 1rem;line-height:1.5;color:#222}}
table{{border-collapse:collapse;width:100%;font-size:.9rem}}th,td{{border:1px solid #ccc;padding:.3rem .5rem;text-align:left}}
th{{background:#f4f4f4}}code{{font-size:.85rem}}</style></head><body>
<h1>Open data audits</h1>
<p>Forensic audits of official energy and shipping data. Open code, error ranges, errors credited.</p>
<h2>Audits</h2>
<ol><li><a href="{REPO}/tree/main/audit01-hormuz">Hormuz tanker flows in IMF PortWatch</a> (draft, Oct 2026)</li></ol>
<h2>Errors credited</h2>
<p>Every error we find or are told about is logged in the <a href="{REPO}/blob/main/ERRORS.md">error ledger (ERRORS.md)</a>.</p>
<h2>Latest watch snapshot</h2>
<p>A scheduled job on GitHub Actions checks IMF PortWatch (Strait of Hormuz), JODI Oil (China crude) and EIA (US crude stocks) every weekday and opens an issue when new data
or a revision of already-published days appears. Times are UTC.</p>
{warn}<table><tr><th>Source</th><th>Latest date</th><th>Latest values</th><th>Publisher last edit</th><th>Checked</th><th>Raw sha256</th></tr>
{chr(10).join(rows) or '<tr><td colspan="6">No snapshot yet.</td></tr>'}
</table>
<p><a href="{REPO}">Source code on GitHub</a> · <a href="{REPO}/issues">Watch alerts (issues)</a> · Code: MIT.
Data: IMF PortWatch (portwatch.imf.org), JODI Oil World Database (jodidata.org), US EIA (eia.gov); only a few summary values are shown here. Snapshots carry OpenTimestamps proofs (.ots) and Wayback Machine copies of the source URLs.</p>
</body></html>
"""
open(os.path.join(ROOT, "docs", "index.html"), "w").write(page)
print("docs/index.html written")
