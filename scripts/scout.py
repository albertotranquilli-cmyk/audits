#!/usr/bin/env python3
"""scout.py - weekly scout of new free tools and data for open-data forensics (stdlib only, no API keys).

Sources (all free and public; each one is optional and non-fatal):
  GitHub repo search (new repos by topic, last 7 days, by stars) and code search (public notebooks that use
  PortWatch/JODI/EIA/ENTSO-E/AGSI; needs a token or an authenticated gh CLI, else skipped); Hacker News Algolia
  (stories and Show HN, last 7 days); Zenodo new datasets; arXiv (cs/econ/physics: AIS, satellite methane, energy
  data quality); CKAN catalogs data.europa.eu and data.gov.uk (new energy datasets); Wayback CDX (new or changed
  files on agency sites: eia.gov, jodidata.org, iea.org, portwatch.imf.org, entsoe.eu, agsi.gie.eu);
  awesome-public-datasets Energy section (diff vs stored copy); 'dark corners' (scripts/dark_corners.py): removed
  agency files still archived, bulk download listings, Internet Archive data uploads, Common Crawl spreadsheets.
Items are scored (stars/points + keyword matches), deduped against data/scout/seen.json; the top 15 new items go to
data/scout/latest.md, the full digest to data/scout/latest.json. One issue per ISO week, titled
'Weekly scout: new free tools & data', when there are new items and a token (GH_TOKEN/GITHUB_TOKEN) or an
authenticated gh CLI is available. Called from watch.py on Mondays (UTC) or with SCOUT_FORCE=1.
"""
import datetime as dt, json, os, re, shutil, subprocess, time, urllib.parse, urllib.request
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIR = os.path.join(ROOT, "data", "scout")
SEEN = os.path.join(DIR, "seen.json")
APD_COPY = os.path.join(DIR, "apd_energy.rst")
REPORT = os.path.join(DIR, "latest.md")
DIGEST = os.path.join(DIR, "latest.json")
CDX_STORE = os.path.join(DIR, "cdx_digests.json")
REPO = "albertotranquilli-cmyk/audits"
TITLE = "Weekly scout: new free tools & data"
TOPICS = ["energy-data", "open-data", "ais", "shipping", "oil", "lng", "data-quality", "forecasting", "osint"]
KW = ["energy", "oil", "gas", "lng", "shipping", "tanker", "satellite", "dataset", "open data", "osint", "ais",
      "refinery", "crude", "port", "vessel", "forecast", "data quality"]
STRONG = re.compile(r"(?i)\b(oil|crude|lng|tankers?|refiner\w*|pipelines?|datasets?|open data|osint|energy|"
                    r"vessels?|ports?|methane|gas|ais|shipping data|maritime)\b")
DEADLINE = [float("inf")]
HN_Q = ["energy", "oil", "gas", "shipping", "tanker", "satellite", "dataset", "open data", "osint"]
APD = "https://raw.githubusercontent.com/awesomedata/awesome-public-datasets/master/README.rst"
UA = "open-data-audits-scout/1.0 (+https://github.com/albertotranquilli-cmyk/audits)"


def token():
    return os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")


def get_json(url, gh=False):
    hd = {"User-Agent": UA, "Accept": "application/vnd.github+json" if gh else "application/json"}
    if gh and token():
        hd["Authorization"] = "Bearer " + token()
    with urllib.request.urlopen(urllib.request.Request(url, headers=hd), timeout=60) as r:
        return json.loads(r.read())


_GH_CLI = None


def gh_cli():
    global _GH_CLI
    if _GH_CLI is None:
        _GH_CLI = bool(shutil.which("gh")) and subprocess.run(["gh", "auth", "status"], capture_output=True).returncode == 0
    return _GH_CLI


def gh_api(path):
    """GitHub REST GET: token from env, else the authenticated gh CLI, else unauthenticated."""
    if not token() and gh_cli():
        r = subprocess.run(["gh", "api", "-X", "GET", path], capture_output=True, text=True, timeout=90)
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[:200])
        return json.loads(r.stdout)
    return get_json("https://api.github.com/" + path, gh=True)


def get_text(url, timeout=60):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def kw_score(text):
    t = (text or "").lower()
    return sum(1 for k in KW if re.search(r"\b" + re.escape(k) + r"\b", t))


def github(since):
    items = {}
    for i, t in enumerate(TOPICS):
        if i:
            time.sleep(2 if (token() or gh_cli()) else 7)  # unauthenticated search: 10 requests/min
        q = urllib.parse.quote(f"topic:{t} created:>={since}")
        try:
            d = gh_api(f"search/repositories?q={q}&sort=stars&order=desc&per_page=10")
        except Exception as e:  # noqa: BLE001
            print(f"::warning::scout github {t}: {e}")
            continue
        for r in d.get("items", []):
            text = f"{r['full_name']} {r.get('description') or ''} {' '.join(r.get('topics', []))}"
            items[f"gh:{r['full_name']}"] = {
                "kind": "repo", "title": r["full_name"], "url": r["html_url"],
                "score": r["stargazers_count"] + 5 * kw_score(text),
                "why": f"★{r['stargazers_count']}, topic {t}: {(r.get('description') or 'no description')[:120]}"}
    return sorted(items.items(), key=lambda kv: -kv[1]["score"])[:10]


def hn(since_ts):
    items = {}
    for q in HN_Q:
        for tag in ("story", "show_hn"):
            u = ("https://hn.algolia.com/api/v1/search?" + urllib.parse.urlencode(
                {"query": q, "tags": tag, "numericFilters": f"created_at_i>{since_ts}", "hitsPerPage": 20}))
            try:
                d = get_json(u)
            except Exception as e:  # noqa: BLE001
                print(f"::warning::scout hn {q}: {e}")
                continue
            for h in d.get("hits", []):
                if not STRONG.search(h.get("title") or ""):
                    continue  # match only in body/url, or only a weak word (e.g. "satellite"): skip
                pts = h.get("points") or 0
                items[f"hn:{h['objectID']}"] = {
                    "kind": "hn", "title": h.get("title"),
                    "url": h.get("url") or f"https://news.ycombinator.com/item?id={h['objectID']}",
                    "score": pts + 5 * kw_score(h.get("title")),
                    "why": f"HN {pts} points, {h.get('num_comments') or 0} comments "
                           f"(https://news.ycombinator.com/item?id={h['objectID']})"}
    return sorted(items.items(), key=lambda kv: -kv[1]["score"])[:10]


def apd():
    txt = urllib.request.urlopen(urllib.request.Request(APD, headers={"User-Agent": UA}), timeout=60).read().decode()
    m = re.search(r"\nEnergy\n[-=~^]+\n(.*?)(?=\n[^\n]+\n[-=~^]{3,}\n)", txt, re.S)
    if not m:
        raise RuntimeError("Energy section not found")
    sec = m.group(1).strip() + "\n"
    old = open(APD_COPY).read() if os.path.exists(APD_COPY) else None
    open(APD_COPY, "w").write(sec)
    if old is None:
        return []  # first run: baseline only
    added = [ln for ln in sec.splitlines() if ln.strip() and ln not in set(old.splitlines())]
    out = []
    for ln in added:
        lm = re.search(r"`([^<`]+?)\s*<([^>]+)>`_", ln)
        if lm:
            out.append((f"apd:{lm.group(2)}", {"kind": "dataset", "title": lm.group(1).strip(), "url": lm.group(2),
                                               "score": 20 + 5 * kw_score(lm.group(1)),
                                               "why": "new or changed entry in awesome-public-datasets, Energy section"}))
    return out


CODE_Q = ['"portwatch.imf.org"', '"jodidata.org"', '"api.eia.gov"', '"agsi.gie.eu"', '"transparency.entsoe.eu"']


def code_search(_since):
    if not (token() or gh_cli()):
        raise RuntimeError("code search needs a token or authenticated gh CLI: skipped")
    out = {}
    for i, q in enumerate(CODE_Q):
        if i:
            time.sleep(7)  # code search: 10 requests/min
        d = gh_api("search/code?" + urllib.parse.urlencode({"q": f"{q} extension:ipynb", "per_page": 5}))
        for it in d.get("items", []):
            repo = it["repository"]["full_name"]
            out[f"code:{repo}/{it['path']}"] = {"kind": "notebook", "title": f"{repo}: {it['path']}", "url": it["html_url"],
                                                "score": 8 + kw_score(it["path"]), "why": f"public notebook using {q.strip(chr(34))}"}
    return list(out.items())


def zenodo(since):
    q = ('(oil OR LNG OR tanker OR shipping OR "AIS" OR refinery OR methane OR "energy data") '
         f'AND publication_date:[{since} TO *]')
    d = get_json("https://zenodo.org/api/records?" + urllib.parse.urlencode(
        {"q": q, "type": "dataset", "sort": "newest", "size": 25}))
    out = []
    for h in d.get("hits", {}).get("hits", []):
        m = h.get("metadata", {})
        t = m.get("title", "")
        out.append((f"zenodo:{h['id']}", {"kind": "dataset", "title": t, "url": h.get("links", {}).get("self_html") or
                                          f"https://zenodo.org/records/{h['id']}", "score": 10 + 5 * kw_score(t),
                                          "why": f"Zenodo dataset, published {m.get('publication_date')}"}))
    return out


def arxiv(since):
    q = ('(abs:"automatic identification system" OR abs:"AIS data" OR abs:"satellite methane" OR abs:"methane plume" '
         'OR abs:"energy data quality" OR abs:"energy statistics" OR abs:"oil tanker" OR abs:"crude oil" '
         'OR abs:"maritime traffic") AND (cat:cs.* OR cat:econ.* OR cat:physics.* OR cat:stat.*)')
    xml = get_text("https://export.arxiv.org/api/query?" + urllib.parse.urlencode(
        {"search_query": q, "sortBy": "submittedDate", "sortOrder": "descending", "max_results": 40}))
    ns = {"a": "http://www.w3.org/2005/Atom"}
    out = []
    for e in ET.fromstring(xml).findall("a:entry", ns):
        pub = e.findtext("a:published", "", ns)[:10]
        if pub < since:
            continue
        t = " ".join(e.findtext("a:title", "", ns).split())
        link = e.findtext("a:id", "", ns)
        out.append((f"arxiv:{link.rsplit('/', 1)[-1].split('v')[0]}", {
            "kind": "paper", "title": t, "url": link, "score": 6 + 5 * kw_score(t),
            "why": f"arXiv {pub}: " + " ".join(e.findtext("a:summary", "", ns).split())[:110]}))
    return out


CKAN = {"data.europa.eu": ("https://data.europa.eu/api/hub/search/ckan/package_search", "issued desc",
                           "https://data.europa.eu/data/datasets/{}"),
        "data.gov.uk": ("https://ckan.publishing.service.gov.uk/api/action/package_search", "metadata_created desc",
                        "https://www.data.gov.uk/dataset/{}")}
# data.gov (catalog.data.gov) is not included: its CKAN API now needs an api.data.gov key.


def ckan(since):
    out = []
    for name, (api, sort, page) in CKAN.items():
        for q in ("energy", "oil", "gas storage", "shipping"):
            try:
                d = get_json(api + "?" + urllib.parse.urlencode({"q": q, "sort": sort, "rows": 20}))
            except Exception as e:  # noqa: BLE001
                print(f"::warning::scout ckan {name} {q}: {e}")
                continue
            for r in d.get("result", {}).get("results", []):
                created = str(r.get("issued") or r.get("metadata_created") or "")[:10]
                if created < since:
                    continue
                t = r.get("title")
                t = t.get("en") or next(iter(t.values()), "") if isinstance(t, dict) else (t or "")
                out.append((f"ckan:{name}:{r.get('id')}", {
                    "kind": "dataset", "title": t, "url": page.format(r.get("name") or r.get("id")),
                    "score": 5 + 5 * kw_score(t), "why": f"new on {name} ({created}), query '{q}'"}))
    return out


CDX_PREFIXES = ["www.eia.gov/dnav/pet/hist_xls/", "www.eia.gov/petroleum/supply/weekly/", "ir.eia.gov/wpsr/",
                "www.jodidata.org/_resources/files/downloads/", "portwatch.imf.org/", "www.iea.org/data-and-statistics/",
                "www.entsoe.eu/", "agsi.gie.eu/"]
FILE_RE = re.compile(r"\.(csv|xlsx?|zip|json|pdf)$", re.I)


def cdx(since):
    store = json.load(open(CDX_STORE)) if os.path.exists(CDX_STORE) else {}
    based = set(store.pop("_baselined_prefixes", []))
    out, seen_now, fresh = [], {}, set()
    for p in CDX_PREFIXES:
        if time.time() > DEADLINE[0]:
            break
        try:
            d = json.loads(get_text("http://web.archive.org/cdx/search/cdx?" + urllib.parse.urlencode(
                {"url": p, "matchType": "prefix", "from": since.replace("-", ""), "output": "json",
                 "fl": "original,timestamp,digest", "filter": "statuscode:200", "limit": 500}), timeout=45) or "[]")
        except Exception as e:  # noqa: BLE001
            print(f"::warning::scout cdx {p}: {e}")
            continue
        for orig, ts, dig in d[1:]:
            u = orig.split("?")[0].replace("http://", "https://")
            seen_now[u] = (ts, dig)
            if p not in based:
                fresh.add(u)  # first successful query of this prefix: baseline only
        based.add(p)
    for u, (ts, dig) in sorted(seen_now.items()):
        old = store.get(u)
        store[u] = dig
        if u in fresh or not FILE_RE.search(u):
            continue  # baseline run, or an HTML page (too noisy): record only
        if old is None or old != dig:
            what = "new file" if old is None else "file changed (new Wayback digest)"
            out.append((f"cdx:{u}:{dig}", {"kind": "agency-file", "title": u.split("/", 3)[-1], "url": u,
                                           "score": 12 if old else 9,
                                           "why": f"{what} on {u.split('/')[2]}, captured {ts[:8]}: "
                                                  f"https://web.archive.org/web/{ts}/{u}"}))
    if len(store) > 8000:
        store = dict(sorted(store.items())[-8000:])
    store["_baselined_prefixes"] = sorted(based)
    json.dump(store, open(CDX_STORE, "w"), indent=0, sort_keys=True)
    return out


def open_issue(body):
    if not token():
        r = subprocess.run(["gh", "issue", "create", "-R", REPO, "--title", TITLE, "--body", body],
                           capture_output=True, text=True, timeout=90)
        if r.returncode:
            raise RuntimeError(r.stderr.strip()[:200])
        return r.stdout.strip()
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/issues", method="POST",
                                 data=json.dumps({"title": TITLE, "body": body}).encode(),
                                 headers={"User-Agent": UA, "Accept": "application/vnd.github+json",
                                          "Authorization": "Bearer " + token()})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())["html_url"]


def run(force=False):
    """Returns True when files under data/scout changed."""
    now = dt.datetime.now(dt.timezone.utc)
    if not (force or os.environ.get("SCOUT_FORCE") == "1" or now.weekday() == 0):
        return False
    os.makedirs(DIR, exist_ok=True)
    seen = json.load(open(SEEN)) if os.path.exists(SEEN) else {"items": {}, "last_issue_week": None}
    since = now - dt.timedelta(days=7)
    found = []
    sd = since.strftime("%Y-%m-%d")
    t0 = time.time()
    DEADLINE[0] = t0 + int(os.environ.get("SCOUT_BUDGET", "480"))  # keeps the Monday run well inside the job timeout
    status = {}
    for name, fn in (("github_repos", lambda: github(sd)), ("github_code", lambda: code_search(sd)),
                     ("hn", lambda: hn(int(since.timestamp()))), ("zenodo", lambda: zenodo(sd)),
                     ("arxiv", lambda: arxiv(sd)), ("ckan", lambda: ckan(sd)), ("wayback_cdx", lambda: cdx(sd)),
                     ("awesome_public_datasets", apd)):
        if time.time() > DEADLINE[0]:
            status[name] = {"ok": False, "error": "time budget exhausted"}
            continue
        try:
            got = fn()
            found += [(k, dict(v, source=name)) for k, v in got]
            status[name] = {"ok": True, "items": len(got)}
        except Exception as e:  # noqa: BLE001
            status[name] = {"ok": False, "error": str(e)[:200]}
            print(f"::warning::scout {name} failed: {e}")
    dark, dark_status = [], {}
    try:
        import dark_corners
        dark, dark_status = dark_corners.run(sd, budget=max(60, min(300, DEADLINE[0] + 120 - time.time())))
    except Exception as e:  # noqa: BLE001
        print(f"::warning::scout dark corners failed: {e}")
    allc = dict(found)
    new_all = sorted(((k, v) for k, v in allc.items() if k not in seen["items"]), key=lambda kv: -kv[1]["score"])
    new, per = [], {}
    for k, v in new_all:  # top 15, at most 4 per source so papers/datasets are not crowded out
        if len(new) < 15 and per.get(v["source"], 0) < 4:
            new.append((k, v))
            per[v["source"]] = per.get(v["source"], 0) + 1
    today = now.strftime("%Y-%m-%d")
    for k, _ in new_all:
        seen["items"][k] = today
    cutoff = (now - dt.timedelta(days=180)).strftime("%Y-%m-%d")
    seen["items"] = {k: d for k, d in seen["items"].items() if d >= cutoff}
    week = now.strftime("%G-W%V")
    body = None
    if new:
        body = (f"Top {len(new)} new items, week {week} (scored by stars/points + keyword matches; "
                f"deduped against `data/scout/seen.json`).\n\n" +
                "\n".join(f"{i}. [{v['title']}]({v['url']}) ({v['kind']}): {v['why']}" for i, (k, v) in enumerate(new, 1)))
        if dark:
            body += f"\n\n**Dark corners** ({len(dark)} findings, full list in `data/scout/latest.json`):\n" + "\n".join(
                f"- [{d['url'][:90]}]({d['url']}) ({d['module']}): {d['why'][:140]} [archive]({d['archive']})" for d in dark[:10])
        open(REPORT, "w").write(f"# {TITLE} ({week})\n\n{body}\n")
        if (token() or gh_cli()) and seen.get("last_issue_week") != week and os.environ.get("SCOUT_NO_ISSUE") != "1":
            try:
                print("scout issue:", open_issue(body))
                seen["last_issue_week"] = week
            except Exception as e:  # noqa: BLE001
                print(f"::warning::scout issue not opened: {e}")
    digest = {"generated_at_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "week": week, "window_start": sd,
              "sources": status, "dark_corners_sources": dark_status, "dark_corners": dark, "top": [dict(v, id=k) for k, v in new],
              "candidates": [dict(v, id=k, new=k in dict(new_all)) for k, v in
                             sorted(allc.items(), key=lambda kv: -kv[1]["score"])]}
    json.dump(digest, open(DIGEST, "w"), indent=1, ensure_ascii=False)
    open(DIGEST, "a").write("\n")
    json.dump(seen, open(SEEN, "w"), indent=1, sort_keys=True)
    open(SEEN, "a").write("\n")
    if os.environ.get("GITHUB_ACTIONS") == "true":
        subprocess.run(["git", "add", "--", DIR], cwd=ROOT, check=False)
    print(f"scout: {len(allc)} candidates, {len(new_all)} new; " + ", ".join(
        f"{k}={'ok:' + str(v['items']) if v['ok'] else 'FAIL'}" for k, v in status.items()))
    return True


if __name__ == "__main__":
    run(force=True)
