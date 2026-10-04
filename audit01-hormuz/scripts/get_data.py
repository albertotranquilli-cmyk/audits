#!/usr/bin/env python3
"""get_data.py - downloads the IMF PortWatch inputs (public ArcGIS REST API). No data is shipped in this repo.

Usage: get_data.py [--fresh]
The query window ends at AUDIT_END (default 2026-09-25, the last port day of the PortWatch release used in
AUDIT #1). Set AUDIT_END=auto to take everything PortWatch currently publishes.
"""
import json, os, sys, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch import fetch

B = "https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services"
FRESH = "--fresh" in sys.argv
GULF_ISO = ("ARE", "SAU", "QAT", "KWT", "BHR", "IRQ", "IRN", "OMN")
START = "2019-01-01"
END = os.environ.get("AUDIT_END", "2026-09-25")
DATE_WHERE = f"date >= DATE '{START}'" + ("" if END == "auto" else f" AND date <= DATE '{END}'")


def q(layer, params):
    base = {"f": "json", "returnGeometry": "false"}
    base.update(params)
    return f"{B}/{layer}/FeatureServer/0/query?" + urllib.parse.urlencode(base)


def paged(layer, params, stem, page=1000):
    off = 0
    while True:
        p = dict(params, resultOffset=off, resultRecordCount=page)
        path = fetch(q(layer, p), f"{stem}_p{off // page:02d}.json", FRESH)
        d = json.load(open(path))
        if "error" in d:
            sys.exit(f"API error {d['error']}")
        if not d.get("exceededTransferLimit") and len(d.get("features", [])) < page:
            break
        off += page


isos = ",".join(f"'{i}'" for i in GULF_ISO)
# 0) layer metadata (records PortWatch's last edit date = the weekly release in use)
for layer in ("Daily_Ports_Data", "Daily_Chokepoints_Data"):
    fetch(f"{B}/{layer}/FeatureServer/0?f=json", f"layerinfo_{layer}.json", FRESH)
# 1) port registry for the Gulf states and Oman
paged("PortWatch_ports_database", {"where": f"ISO3 IN ({isos})",
      "outFields": "portid,portname,country,ISO3,lat,lon", "orderByFields": "portid"}, "ports_db_gulf")
# 2) daily transits, Strait of Hormuz (chokepoint6)
paged("Daily_Chokepoints_Data", {"where": f"portid='chokepoint6' AND {DATE_WHERE}",
      "outFields": "date,portid,n_tanker,capacity_tanker", "orderByFields": "date"}, "chokepoint6_daily")
# 3) daily port data, aggregated server-side to port x month
stats = [{"statisticType": "sum", "onStatisticField": f, "outStatisticFieldName": f}
         for f in ("portcalls_tanker", "export_tanker", "import_tanker")]
stats.append({"statisticType": "count", "onStatisticField": "ObjectId", "outStatisticFieldName": "n_days"})
paged("Daily_Ports_Data", {"where": f"ISO3 IN ({isos}) AND {DATE_WHERE}",
      "outStatistics": json.dumps(stats), "groupByFieldsForStatistics": "portid,portname,ISO3,year,month",
      "orderByFields": "portid,year,month"}, "ports_monthly_gulf")
# 4) daily records of one terminal (Bandar-E Pars Terminal, port105), for the burst-day filter
paged("Daily_Ports_Data", {"where": f"portid='port105' AND date >= DATE '2024-01-01'"
      + ("" if END == "auto" else f" AND date <= DATE '{END}'"),
      "outFields": "date,portid,portcalls_tanker,export_tanker,import_tanker", "orderByFields": "date"},
      "port105_daily")
print("raw data ready (window end: %s)" % END)
