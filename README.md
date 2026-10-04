# Official data, audited in public

Forensic audits of official and reference data on energy and physical flows. Every audit reruns with one command from free public sources, states its limits, and puts an uncertainty range on every number. Errors found by others, and our own, are logged in [ERRORS.md](ERRORS.md).

| # | Audit | Data | Status |
|---|---|---|---|
| 1 | [Hormuz tanker flows in IMF PortWatch](audit01-hormuz/) | IMF PortWatch | Draft, Oct 2026 |

Code: MIT. Source data is not redistributed here; `run.sh --fresh` downloads it from the original publisher.

## Watch

A scheduled GitHub Actions job ([`.github/workflows/watch.yml`](.github/workflows/watch.yml)) checks IMF PortWatch's
Strait of Hormuz daily transits every weekday, stores a compact snapshot in [`data/watch/`](data/watch/) and opens an
issue when new data or a revision of already-published days appears. Summary page: https://albertotranquilli-cmyk.github.io/audits/
