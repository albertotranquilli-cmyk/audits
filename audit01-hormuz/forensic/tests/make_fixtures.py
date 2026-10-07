#!/usr/bin/env python3
"""make_fixtures.py - writes a SMALL SYNTHETIC raw directory in the PortWatch ArcGIS JSON layout.

No PortWatch data: every number is invented with a closed-form rule so tests can check exact answers.
World: 4 ports (2 inside the Gulf incl. a fake 'port105', 2 outside), 2019-01-01..2026-09-25.
  KWT 'portA' (inside): export 30,000 t/day, import 0, 1 tanker call/day; from 2026-03-01 export 15,000 t/day.
  IRN 'port105' (inside): export 1,000 t/day on the 1st of each month only (1 call); on 2026-03-07: 40 calls,
                          export 2,000,000 t (a burst day).
  OMN 'portC', ARE 'portD' (outside, Fujairah-like): export 50,000 t/day (must never be counted).
  chokepoint6: 2 tankers/day, capacity_tanker 60,000 t/day; from 2026-03-01: 1 tanker, 1,000 t/day.
"""
import calendar, datetime as dt, json, os, sys

START, END = dt.date(2019, 1, 1), dt.date(2026, 9, 25)
CRISIS = dt.date(2026, 3, 1)
PORTS = [("portA", "Synthetic Kuwait A", "KWT", 29.0, 48.1), ("port105", "Synthetic Terminal", "IRN", 27.56, 52.51),
         ("portC", "Synthetic Oman C", "OMN", 24.5, 56.6), ("portD", "Synthetic Fujairah D", "ARE", 25.2, 56.36)]


def days():
    d = START
    while d <= END:
        yield d
        d += dt.timedelta(1)


def port_day(pid, d):
    if pid == "portA":
        return dict(portcalls_tanker=1, export_tanker=15000 if d >= CRISIS else 30000, import_tanker=0)
    if pid == "port105":
        if d == dt.date(2026, 3, 7):
            return dict(portcalls_tanker=40, export_tanker=2000000, import_tanker=0)
        return dict(portcalls_tanker=1 if d.day == 1 else 0, export_tanker=1000 if d.day == 1 else 0, import_tanker=0)
    return dict(portcalls_tanker=1, export_tanker=50000, import_tanker=0)


def page(rows, fields):
    return {"objectIdFieldName": "ObjectId", "fields": [{"name": f} for f in fields], "features": [{"attributes": r} for r in rows]}


def write(out, epoch_dates=False):
    os.makedirs(out, exist_ok=True)
    def j(name, obj):
        with open(os.path.join(out, name), "w") as fh:
            json.dump(obj, fh)
    j("ports_db_gulf_p00.json", page([dict(portid=p, portname=n, country=c, ISO3=c, lat=la, lon=lo) for p, n, c, la, lo in PORTS],
                                      ["portid", "portname", "country", "ISO3", "lat", "lon"]))
    def ds(d):
        return int(dt.datetime(d.year, d.month, d.day, tzinfo=dt.timezone.utc).timestamp() * 1000) if epoch_dates else d.isoformat()
    ch = [dict(date=ds(d), portid="chokepoint6", n_tanker=1 if d >= CRISIS else 2, capacity_tanker=1000 if d >= CRISIS else 60000)
          for d in days()]
    j("chokepoint6_daily_p00.json", page(ch, ["date", "portid", "n_tanker", "capacity_tanker"]))
    agg = {}
    for p, n, c, _, _ in PORTS:
        for d in days():
            k = (p, d.year, d.month)
            a = agg.setdefault(k, dict(portcalls_tanker=0, export_tanker=0, import_tanker=0, n_days=0, portid=p, portname=n,
                                       ISO3=c, year=d.year, month=d.month))
            for f, v in port_day(p, d).items():
                a[f] += v
            a["n_days"] += 1
    j("ports_monthly_gulf_p00.json", page(list(agg.values()), ["portcalls_tanker", "export_tanker", "import_tanker", "n_days",
                                                               "portid", "portname", "ISO3", "year", "month"]))
    bp = [dict(date=ds(d), portid="port105", **port_day("port105", d)) for d in days() if d >= dt.date(2024, 1, 1)]
    j("port105_daily_p00.json", page(bp, ["date", "portid", "portcalls_tanker", "export_tanker", "import_tanker"]))
    for layer, ms in (("Daily_Ports_Data", 1791312087589), ("Daily_Chokepoints_Data", 1791288541457)):
        flds = ([("capacity_tanker", "esriFieldTypeInteger"), ("n_tanker", "esriFieldTypeInteger")] if "Choke" in layer else
                [("export_tanker", "esriFieldTypeInteger"), ("import_tanker", "esriFieldTypeInteger"), ("portcalls_tanker", "esriFieldTypeInteger")])
        j(f"layerinfo_{layer}.json", {"name": layer, "editingInfo": {"lastEditDate": ms},
                                      "fields": [dict(name=f, alias=f, type=t, description=None) for f, t in flds]})
    return out


if __name__ == "__main__":
    print(write(sys.argv[1] if len(sys.argv) > 1 else "synthetic_raw"))
