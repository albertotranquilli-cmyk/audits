# Protocol status

Every protocol version and its status. Protocol files are never edited after commit; only this file changes.

| Version | File | sha256 | OpenTimestamps proof | Committed (UTC) | Status | Notes |
|---|---|---|---|---|---|---|
| Protocol-1 | engine/PROTOCOL.md | d3d5ec7a46195268b1325594f8b1f08c941822629693249aed43a28acc1d3523 | engine/PROTOCOL.md.ots | 2026-10-04 | registered, not started | Start 2026-10-07 00:00 UTC. Engine code freeze commit: (to be recorded here before start) |

Verify: `sha256sum engine/PROTOCOL.md` and `ots verify engine/PROTOCOL.md.ots` (the Bitcoin attestation is added a
few hours after stamping by the scheduled `ots upgrade`).
