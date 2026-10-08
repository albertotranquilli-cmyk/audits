# Pre-registration hashes

Each pre-registration file is committed first, then hashed. The hash cannot live inside the file it covers, so it is recorded here and in the X post. After registration a file is never edited; corrections go in `ERRORS.md` with a timestamp.

| File | Registered (UTC) | Commit | sha256 of the committed file |
|---|---|---|---|
| `prereg/PREREG_01.md` | 2026-10-08T20:15Z | `aca16ab8cef892040425f7c23e3b757f5d35e5cf` | `1b0ff87b464a935ab1741e9bc512a0948184fceb2eeb6470643e69b0c44d7dd5` |

PRE-REG #1 note: the published slot was 2026-10-08 07:30 UTC and was missed. It was registered 12 h 45 min late. At registration, `primaryyear2026.csv` on jodidata.org still reported `Last-Modified: Tue, 22 Sep 2026 07:18:47 GMT`, i.e. no August 2026 data had been published.

Verify: `curl -s https://raw.githubusercontent.com/albertotranquilli-cmyk/audits/aca16ab8cef892040425f7c23e3b757f5d35e5cf/prereg/PREREG_01.md | sha256sum`
