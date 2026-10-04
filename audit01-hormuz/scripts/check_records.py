#!/usr/bin/env python3
"""check_records.py - compares the downloaded PortWatch records with manifests/raw_records_SHA256SUMS.

Hashes are taken over the parsed records (JSON features, keys sorted), not over raw bytes, because the API's
byte serialisation can change while the records stay the same. Layer metadata files are not compared.
Usage: check_records.py            -> compare and report
       check_records.py --write    -> rewrite the manifest from the current download (maintainers only)
"""
import glob, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW, MAN = os.path.join(ROOT, "data", "raw"), os.path.join(ROOT, "manifests", "raw_records_SHA256SUMS")


def digest(path):
    feats = json.load(open(path))["features"]
    return hashlib.sha256(json.dumps(feats, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


cur = {os.path.basename(p): digest(p) for p in sorted(glob.glob(os.path.join(RAW, "*_p*.json")))}
if "--write" in sys.argv:
    with open(MAN, "w") as f:
        f.writelines(f"{h}  {n}\n" for n, h in cur.items())
    print(f"manifest written: {len(cur)} files"); sys.exit(0)
if not os.path.exists(MAN):
    print("no manifest found; skipping record check"); sys.exit(0)
ref = dict(reversed(l.split()) for l in open(MAN) if l.strip())
diff = sorted(n for n in set(cur) | set(ref) if cur.get(n) != ref.get(n))
if not diff:
    print(f"records: all {len(cur)} files match the AUDIT #1 manifest (same PortWatch records)")
else:
    print(f"NOTE: {len(diff)} file(s) differ from the AUDIT #1 manifest: {', '.join(diff)}")
    print("      PortWatch revises past data weekly; numbers may differ from the published thread.")
