#!/usr/bin/env python3
"""fetch.py - polite, read-only downloader.

- Fixed, truthful User-Agent (override with the AUDIT_UA environment variable).
- robots.txt is checked before the first request to each host (RFC 9309: 4xx = no restriction,
  5xx or unreachable = stop).
- At least 6 s between requests to the same host; honours Retry-After on 429/503 (max 3 retries).
- Raw responses are written to data/raw/<name> and never modified. Each download appends a provenance
  record (url, retrieval time in UTC, HTTP status, bytes, sha256) to data/provenance.jsonl.
- An existing file is reused unless fresh=True.
"""
import datetime as dt, hashlib, json, os, sys, time
import urllib.error, urllib.parse, urllib.request, urllib.robotparser

UA = os.environ.get("AUDIT_UA", "audit01-hormuz/1.0 (read-only research script; see README)")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
PROV = os.path.join(ROOT, "data", "provenance.jsonl")
MIN_INTERVAL = 6.0
_last, _robots = {}, {}


def now_utc():
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _get(url, timeout=90):
    host = urllib.parse.urlsplit(url).hostname
    for attempt in range(4):
        wait = _last.get(host, 0) + MIN_INTERVAL - time.time()
        if wait > 0:
            time.sleep(wait)
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                _last[host] = time.time()
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            _last[host] = time.time()
            if e.code in (429, 503) and attempt < 3:
                ra = e.headers.get("Retry-After", "")
                time.sleep(min(int(ra), 600) if ra.isdigit() else 30 * 2 ** attempt)
                continue
            return e.code, e.read()
    raise RuntimeError("retries exhausted: " + url)


def robots_ok(url):
    p = urllib.parse.urlsplit(url)
    root = f"{p.scheme}://{p.netloc}"
    if root not in _robots:
        try:
            st, body = _get(root + "/robots.txt")
        except Exception as e:
            sys.exit(f"[fetch] robots.txt unreachable for {root} ({e}); stopping")
        if st >= 500:
            sys.exit(f"[fetch] robots.txt HTTP {st} for {root}: treated as disallow; stopping")
        rp = urllib.robotparser.RobotFileParser()
        rp.parse([] if st >= 400 else body.decode("utf-8", "replace").splitlines())
        _robots[root] = (rp, st)
    rp, st = _robots[root]
    return rp.can_fetch(UA, url), st


def fetch(url, name, fresh=False):
    os.makedirs(RAW, exist_ok=True)
    path = os.path.join(RAW, name)
    if os.path.exists(path) and not fresh:
        return path
    ok, rst = robots_ok(url)
    if not ok:
        sys.exit(f"[fetch] robots.txt disallows {url}")
    st, body = _get(url)
    if st != 200:
        sys.exit(f"[fetch] HTTP {st} for {url}: {body[:300]!r}")
    with open(path, "wb") as f:
        f.write(body)
    rec = {"name": name, "url": url, "retrieved_at_utc": now_utc(), "http_status": st, "bytes": len(body),
           "sha256": hashlib.sha256(body).hexdigest(), "robots_status": rst}
    with open(PROV, "a") as f:
        f.write(json.dumps(rec) + "\n")
    sys.stderr.write(f"[fetch] {name}: {len(body)} B sha256={rec['sha256'][:16]}\n")
    return path
