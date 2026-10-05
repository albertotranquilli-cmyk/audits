# audits — one-page summary

**What it is:** forensic audits of official and reference data on energy and physical flows. Every audit reruns with one command from free public sources, states its limits, and puts an uncertainty range on every number. Errors found by others — and our own — are logged in ERRORS.md.

**Current audit:** Hormuz tanker flows in IMF PortWatch (draft, Oct 2026). Code: MIT. Source data is not redistributed; `run.sh --fresh` downloads it from the original publisher.

**Infrastructure that runs on its own:**
- A scheduled GitHub Actions job checks every weekday: IMF PortWatch daily transits through the Strait of Hormuz, JODI Oil World Database China crude, and EIA weekly US commercial crude stocks.
- Snapshots are stored with OpenTimestamps proofs (`.ots`) — independently verifiable timestamps, no trusted third party.
- Source URLs are saved to the Wayback Machine when they change.
- An issue is opened automatically when new data or a revision of already-published values appears.

**Design principle:** the audit is the artifact, not the conclusion. Anyone can rerun it, check the hashes, and verify the timestamps. Public summary page: https://albertotranquilli-cmyk.github.io/audits/

Link: https://github.com/albertotranquilli-cmyk/audits