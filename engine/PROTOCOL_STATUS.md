# Protocol status

Every protocol version and its status. Protocol files are never edited after commit; only this file changes.

| Version | File | sha256 | OpenTimestamps proof | Committed | Status |
|---|---|---|---|---|---|
| Protocol-1 | engine/PROTOCOL.md | d3d5ec7a46195268b1325594f8b1f08c941822629693249aed43a28acc1d3523 | engine/PROTOCOL.md.ots | commit 677a6c1656b460cae1e0d071517b911711c0575b (2026-10-04) | INVALIDATED_PRE_RUN |

## Protocol-1: INVALIDATED_PRE_RUN (2026-10-04)

Protocol-1 failed the pre-audit against its specification. The experiment itself did not fail: it never started.
**No discovery set was opened, no evaluation data were queried, no results were observed.**
The original file, its hash, its OpenTimestamps proof and its commit are kept unchanged.

Reasons:
1. There is no irrevocable 30/10/10 issuer split; Protocol-1 uses period-based and row-hash splits instead.
2. SEC EDGAR is not the primary domain. UN Comtrade, scout-discovered tables and official statistics are mixed into
   the invention set instead of being kept as the hold-out domain.
3. A library of 9 predefined test classes contradicts the specification: at most 3 seed detectors plus a generator
   that searches for relations over a program grammar.
4. The weight w_i is assigned by publisher tier, not by outcome class and materiality defined ex ante.
5. The ex-ante outcome taxonomy (semantic/economic, reporting/accounting, data-pipeline artifact, unresolved) is
   missing or not binding.
6. A fixed start date of 2026-10-07 comes before the ex-ante red-team and the code freeze.

Process lesson: the protocol text was not checked against the specification, item by item, before it was hashed.
From now on every protocol version is checked item by item against its specification before it is hashed and
committed.

A successor protocol is in draft and unregistered. It will be listed here only once it is committed, hashed and
timestamped.
