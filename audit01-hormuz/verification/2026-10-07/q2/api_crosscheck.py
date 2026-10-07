#!/usr/bin/env python3
"""Independent read-only cross-check against the live PortWatch ArcGIS API (server-side sums, own query formulation).
Run recompute.py first (reads the 45-port list from recompute_out.json). Sends 6 queries, 6 s apart.
Writes api/<query>.json (raw API responses; not committed, PortWatch data), api/provenance.jsonl (URL, UTC time, sha256)
and api/summary.json. Results depend on the PortWatch weekly release live at run time."""
import json, urllib.parse, urllib.request, time, hashlib, datetime, os, statistics
B = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "api")
os.makedirs(out_dir, exist_ok=True)
inside = [p.split(":")[1] for p in json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "recompute_out.json")))["inside_ports"]]
ids = ",".join(f"'{p}'" for p in inside)
def st(fields, kind="sum"):
    return json.dumps([{"statisticType": kind, "onStatisticField": f, "outStatisticFieldName": f"{kind}_{f}"} for f in fields])
Q = {
 "ports_window_by_iso": ("Daily_Ports_Data", {"where": f"portid IN ({ids}) AND date >= DATE '2026-03-01' AND date <= DATE '2026-09-25'",
     "outStatistics": st(["export_tanker", "import_tanker"]), "groupByFieldsForStatistics": "ISO3"}),
 "port105_window": ("Daily_Ports_Data", {"where": "portid='port105' AND date >= DATE '2026-03-01' AND date <= DATE '2026-09-25'",
     "outStatistics": st(["export_tanker", "import_tanker", "portcalls_tanker"])}),
 "port105_202506": ("Daily_Ports_Data", {"where": "portid='port105' AND date >= DATE '2025-06-01' AND date <= DATE '2025-06-30'",
     "outStatistics": st(["export_tanker", "import_tanker", "portcalls_tanker"])}),
 "port105_20260228": ("Daily_Ports_Data", {"where": "portid='port105' AND date = DATE '2026-02-28'", "outFields": "date,portcalls_tanker,export_tanker,import_tanker"}),
 "port105_monthly_2019_2024": ("Daily_Ports_Data", {"where": "portid='port105' AND date >= DATE '2019-01-01' AND date <= DATE '2024-12-31'",
     "outStatistics": st(["portcalls_tanker"]), "groupByFieldsForStatistics": "year,month", "orderByFields": "year,month"}),
 "chokepoint6_window": ("Daily_Chokepoints_Data", {"where": "portid='chokepoint6' AND date >= DATE '2026-03-01' AND date <= DATE '2026-09-25'",
     "outStatistics": st(["capacity_tanker", "n_tanker"])}),
}
prov = open(os.path.join(out_dir, "provenance.jsonl"), "a")
res = {}
for k, (layer, p) in Q.items():
    p = dict(p, f="json", returnGeometry="false")
    url = f"{B}/{layer}/FeatureServer/0/query?" + urllib.parse.urlencode(p)
    body = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "audit01-verify/1.0 (read-only)"}), timeout=90).read()
    open(os.path.join(out_dir, k + ".json"), "wb").write(body)
    prov.write(json.dumps({"name": k, "url": url, "retrieved_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                           "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()}) + "\n")
    res[k] = [f["attributes"] for f in json.loads(body)["features"]]
    time.sleep(6)
w = res["ports_window_by_iso"]
net = sum(r["sum_export_tanker"] - r["sum_import_tanker"] for r in w)
irn = sum(r["sum_export_tanker"] - r["sum_import_tanker"] for r in w if r["ISO3"] == "IRN")
C = res["chokepoint6_window"][0]["sum_capacity_tanker"]
bp = res["port105_window"][0]; bpn = bp["sum_export_tanker"] - bp["sum_import_tanker"]
calls = [r["sum_portcalls_tanker"] for r in res["port105_monthly_2019_2024"]]
summary = {"net_Mt": net/1e6, "C_Mt": C/1e6, "gap_Mt": (net-C)/1e6, "BP_net_Mt": bpn/1e6, "gap_excl_BP_Mt": (net-C-bpn)/1e6,
           "gap_excl_IRN_Mt": (net-C-irn)/1e6, "BP_202506": res["port105_202506"][0], "BP_20260228": res["port105_20260228"],
           "BP_months_2019_2024": len(calls), "BP_median_calls_2019_2024": statistics.median(calls)}
json.dump(summary, open(os.path.join(out_dir, "summary.json"), "w"), indent=1)
print(json.dumps(summary, indent=1))
