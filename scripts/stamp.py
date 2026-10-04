#!/usr/bin/env python3
"""stamp.py - OpenTimestamps proofs for files under prereg/ and data/watch/ (free public OTS calendars).

For every target file, <file>.ots is created when missing or when it no longer matches the file's sha256
(the old proof stays in git history). Pending proofs are upgraded with `ots upgrade` (Bitcoin attestation
arrives a few hours after stamping). In GitHub Actions the proofs are staged with `git add`.
Prints and returns the list of proof files that were created or upgraded. Never fails the run.
"""
import glob, hashlib, os, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP = {"status.json", ".summary.md"}


def ots_cmd():
    for attempt in (0, 1):
        if attempt:
            subprocess.run([sys.executable, "-m", "pip", "install", "-q", "opentimestamps-client"], check=False)
        for c in (["ots"], [os.path.expanduser("~/.local/bin/ots")]):
            try:
                if subprocess.run(c + ["--version"], capture_output=True).returncode == 0:
                    return c
            except FileNotFoundError:
                pass
    raise RuntimeError("opentimestamps-client not available")



def proof_digest(path):
    """sha256 digest stored in a .ots file (header magic, version byte, op 0x08, 32-byte digest)."""
    b = open(path, "rb").read()
    magic = b"\x00OpenTimestamps\x00\x00Proof\x00\xbf\x89\xe2\xe8\x84\xe8\x92\x94"
    if not b.startswith(magic) or b[len(magic) + 1] != 0x08:
        return None
    i = len(magic) + 2
    return b[i:i + 32].hex()


def targets():
    fs = [p for p in glob.glob(os.path.join(ROOT, "prereg", "**", "*"), recursive=True)]
    fs += glob.glob(os.path.join(ROOT, "data", "watch", "*"))
    fs += glob.glob(os.path.join(ROOT, "engine", "PROTOCOL*.md"))
    return sorted(p for p in fs if os.path.isfile(p) and not p.endswith((".ots", ".bak"))
                  and os.path.basename(p) not in SKIP)


def run():
    touched = []
    try:
        ots = ots_cmd()
    except Exception as e:  # noqa: BLE001
        print(f"::warning::stamp: {e}")
        return touched
    for f in targets():
        p = f + ".ots"
        sha = hashlib.sha256(open(f, "rb").read()).hexdigest()
        try:
            if not os.path.exists(p) or proof_digest(p) != sha:
                if os.path.exists(p):
                    os.remove(p)
                r = subprocess.run(ots + ["stamp", f], capture_output=True, text=True, timeout=120)
                if r.returncode == 0 and os.path.exists(p):
                    touched.append(p)
                else:
                    print(f"::warning::ots stamp failed for {f}: {r.stderr.strip()[-300:]}")
                continue
            before = open(p, "rb").read()
            subprocess.run(ots + ["upgrade", p], capture_output=True, text=True, timeout=120)
            if os.path.exists(p + ".bak"):
                os.remove(p + ".bak")
            if open(p, "rb").read() != before:
                touched.append(p)
        except Exception as e:  # noqa: BLE001
            print(f"::warning::ots error for {f}: {e}")
    if touched and os.environ.get("GITHUB_ACTIONS") == "true":
        subprocess.run(["git", "add", "--"] + touched, cwd=ROOT, check=False)
    for p in touched:
        print("proof updated:", os.path.relpath(p, ROOT))
    return touched


if __name__ == "__main__":
    run()
