#!/usr/bin/env python3
"""dark_corners.py - public but poorly visible data on agency sites (legal, public, no login, robots.txt respected).

  removed:   Wayback CDX - CSV/XLS(X)/PDF/ZIP files that were archived with HTTP 200 and later archived as 404/410
             (removed or moved), confirmed by a polite live HEAD check; archived copy link included.
  listings:  public download pages / bulk folders / manifests on those sites; new file links vs the stored set.
  ia:        Internet Archive advancedsearch, mediatype=data uploads matching oil/tanker/AIS/refinery/energy.
  commoncrawl: Common Crawl index, CSV/XLS(X) files on those domains not linked from the watched pages.
run(since) -> list of findings {module, url, why, archive}. Each module is time-boxed and non-fatal.
Stdlib only. State in data/scout/dark_state.json.
"""
import json, os, re, time, urllib.parse, urllib.request, urllib.robotparser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE = os.path.join(ROOT, "data", "scout", "dark_state.json")
UA = "open-data-audits-scout/1.0 (+https://github.com/albertotranquilli-cmyk/audits)"
FILE_RE = re.compile(r"\.(csv|xlsx?|pdf|zip)$", re.I)
PREFIXES = ["www.eia.gov/petroleum/", "ir.eia.gov/", "www.jodidata.org/_resources/files/downloads/",
            "iea.blob.core.windows.net/assets/", "portwatch.imf.org/", "www.opec.org/opec_web/static_files_project/",
            "www.stats.gov.cn/english/", "english.customs.gov.cn/", "www.entsoe.eu/Documents/", "agsi.gie.eu/"]
LISTINGS = ["https://api.eia.gov/bulk/manifest.txt", "https://ir.eia.gov/wpsr/",
            "https://www.jodidata.org/oil/database/data-downloads.aspx",
            "https://www.jodidata.org/_resources/files/downloads/oil-data/annual-csv/primary/",
            "https://www.opec.org/opec_web/en/publications/202.htm", "https://www.entsoe.eu/data/",
            "https://agsi.gie.eu/data-overview", "https://www.stats.gov.cn/english/PressRelease/"]
IA_TITLE = re.compile(r"(?i:\b(oil|tankers?|refiner\w*|crude|lng|energy statistics|shipping)\b)|\bAIS\b")
IA_SKIP = ("miraheze-wiki", "osf-registrations", "wiki-")
_robots = {}


def get(url, timeout=45, method="GET"):
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, (r.read() if method == "GET" else b"")


def robots_ok(url):
    p = urllib.parse.urlsplit(url)
    base = f"{p.scheme}://{p.netloc}"
    if base not in _robots:
        rp = urllib.robotparser.RobotFileParser(base + "/robots.txt")
        try:
            rp.parse(get(base + "/robots.txt", timeout=20)[1].decode("utf-8", "replace").splitlines())
        except Exception:  # noqa: BLE001
            rp = None  # no robots.txt reachable: treat as allowed
        _robots[base] = rp
    rp = _robots[base]
    return rp is None or rp.can_fetch(UA, url)


def cdx(params, timeout=45):
    body = get("http://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(params, doseq=True), timeout)[1]
    d = json.loads(body or b"[]")
    return d[1:] if d else []


def removed(state, deadline):
    out, known = [], set(state.setdefault("removed", []))
    for p in PREFIXES:
        if time.time() > deadline:
            break
        try:
            ok = cdx({"url": p, "matchType": "prefix", "from": "2019", "output": "json", "fl": "original,timestamp",
                      "filter": ["statuscode:200", "original:.*\\.(csv|xlsx?|pdf|zip|CSV|XLSX?|PDF|ZIP)$"],
                      "collapse": "urlkey", "limit": 3000})
            gone = cdx({"url": p, "matchType": "prefix", "from": "2019", "output": "json", "fl": "original,timestamp",
                        "filter": ["statuscode:(404|410)", "original:.*\\.(csv|xlsx?|pdf|zip|CSV|XLSX?|PDF|ZIP)$"],
                        "limit": 3000})
        except Exception as e:  # noqa: BLE001
            print(f"::warning::dark removed {p}: {e}")
            continue
        first200 = {}
        for u, ts in ok:
            first200.setdefault(u, ts)
        cand = {}
        for u, ts in gone:
            if u in first200 and ts > first200[u] and u not in known:
                cand[u] = max(ts, cand.get(u, ""))
        for u, ts404 in sorted(cand.items(), key=lambda kv: kv[1], reverse=True)[:5]:
            if time.time() > deadline:
                break
            live = "not checked"
            if robots_ok(u):
                try:
                    live = str(get(u, timeout=20, method="HEAD")[0])
                except Exception as e:  # noqa: BLE001
                    live = str(getattr(e, "code", "error"))
                time.sleep(2)
            if live.startswith("2"):
                continue  # back online: not removed
            known.add(u)
            out.append({"module": "removed", "url": u, "archive": f"https://web.archive.org/web/{first200[u]}id_/{u}",
                        "why": f"archived OK on {first200[u][:8]}, archived as missing on {ts404[:8]}, live check {live}: "
                               "a file the publisher no longer serves; the archived copy can show what changed"})
    state["removed"] = sorted(known)[-3000:]
    return out


def links(url, body):
    txt = body.decode("utf-8", "replace")
    if url.endswith("manifest.txt"):
        d = json.loads(txt).get("dataset", {})
        return {f"{v.get('accessURL')}#{v.get('last_updated')}" for v in d.values()}
    return {urllib.parse.urljoin(url, h) for h in re.findall(r'href=["\']([^"\'#]+)', txt, re.I)
            if FILE_RE.search(h.split("?")[0])}


def listings(state, deadline):
    out, store = [], state.setdefault("listings", {})
    for u in LISTINGS:
        if time.time() > deadline or not robots_ok(u):
            continue
        try:
            fs = links(u, get(u, timeout=45)[1])
        except Exception as e:  # noqa: BLE001
            print(f"::warning::dark listing {u}: {e}")
            continue
        time.sleep(2)
        old = store.get(u)
        store[u] = sorted(fs)[:2000]
        if old is None:
            continue  # baseline
        for f in sorted(fs - set(old))[:20]:
            fu = f.split("#")[0]
            why = ("EIA bulk dataset updated (" + f.split("#")[1] + ")") if "#" in f else f"new file link on {u}"
            out.append({"module": "listings", "url": fu, "why": why, "archive": f"https://web.archive.org/web/2/{fu}"})
    return out


def ia(since, state, deadline):
    q = ('(title:(oil OR tanker OR AIS OR refinery OR "energy statistics" OR crude OR LNG) OR '
         'subject:(oil OR tanker OR AIS OR refinery OR "energy statistics")) AND mediatype:data '
         f'AND addeddate:[{since} TO null]')
    u = "https://archive.org/advancedsearch.php?" + urllib.parse.urlencode(
        [("q", q), ("fl[]", "identifier"), ("fl[]", "title"), ("fl[]", "addeddate"), ("fl[]", "downloads"),
         ("fl[]", "description"), ("sort[]", "addeddate desc"), ("rows", "50"), ("output", "json")])
    docs = json.loads(get(u, timeout=60)[1]).get("response", {}).get("docs", [])
    known, out = set(state.setdefault("ia", [])), []
    for d in docs:
        i = d["identifier"]
        if i in known or i.startswith(IA_SKIP) or not IA_TITLE.search(str(d.get("title") or "")):
            continue
        known.add(i)
        desc = d.get("description") or ""
        desc = " ".join(desc) if isinstance(desc, list) else desc
        out.append({"module": "ia", "url": f"https://archive.org/details/{i}", "archive": f"https://archive.org/download/{i}",
                    "why": f"Internet Archive data upload {str(d.get('addeddate'))[:10]}, {d.get('downloads', 0)} downloads, "
                           f"{'no description' if len(desc) < 20 else 'described'}: {str(d.get('title'))[:100]}"})
    state["ia"] = sorted(known)[-3000:]
    return out


def commoncrawl(state, deadline):
    cols = json.loads(get("http://index.commoncrawl.org/collinfo.json", timeout=30)[1])
    api = cols[0]["cdx-api"].replace("https://", "http://")
    linked = set()
    for v in state.get("listings", {}).values():
        linked |= {x.split("#")[0] for x in v}
    known, out = set(state.setdefault("commoncrawl", [])), []
    fails = 0
    for pre in PREFIXES:  # domain-wide filtered queries time out; prefix scans + client-side filter
        if time.time() > deadline or fails >= 2:
            break  # index overloaded: try again next week
        try:
            body = get(api + "?" + urllib.parse.urlencode({"url": pre, "matchType": "prefix", "output": "json",
                                                           "fl": "url,mime,status,timestamp", "limit": 2000}), timeout=30)[1]
            fails = 0
        except Exception as e:  # noqa: BLE001
            if getattr(e, "code", None) != 404:
                fails += 1
                print(f"::warning::dark commoncrawl {pre}: {e}")
            continue
        for ln in body.decode("utf-8", "replace").splitlines():
            try:
                r = json.loads(ln)
            except ValueError:
                continue
            u = r.get("url", "")
            if r.get("status") != "200" or not re.search(r"\.(csv|xlsx?)$", u.split("?")[0], re.I) or u in known:
                continue
            known.add(u)
            if u in linked:
                continue
            out.append({"module": "commoncrawl", "url": u, "archive": f"https://web.archive.org/web/2/{u}",
                        "why": f"spreadsheet on {pre.split('/')[0]} seen by Common Crawl {cols[0]['id']} "
                               f"({str(r.get('timestamp'))[:8]}), not linked from the watched download pages"})
        time.sleep(2)
    state["commoncrawl"] = sorted(known)[-5000:]
    return out[:40]


def run(since, budget=300):
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    deadline = time.time() + budget
    found, status = [], {}
    for name, fn in (("listings", lambda: listings(state, deadline)), ("ia", lambda: ia(since, state, deadline)),
                     ("commoncrawl", lambda: commoncrawl(state, deadline)), ("removed", lambda: removed(state, deadline))):
        if time.time() > deadline:
            status[name] = {"ok": False, "error": "time budget exhausted"}
            continue
        try:
            got = fn()
            found += got
            status[name] = {"ok": True, "items": len(got)}
        except Exception as e:  # noqa: BLE001
            status[name] = {"ok": False, "error": str(e)[:200]}
            print(f"::warning::dark {name}: {e}")
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    json.dump(state, open(STATE, "w"), indent=0, sort_keys=True)
    return found, status


if __name__ == "__main__":
    import sys
    f, s = run(sys.argv[1] if len(sys.argv) > 1 else "2026-09-27")
    print(json.dumps(s), len(f))
    for x in f[:20]:
        print(x["module"], x["url"], "|", x["why"][:120])
