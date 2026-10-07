# Sources for the 2026-10-07 verification

All documents were retrieved on 2026-10-07 between 21:12 and 21:15 UTC. SHA-256 is of the exact bytes received.
Only the two ArcGIS layer metadata files are committed ([metadata/](metadata/)). Third-party documents (IMF papers,
PortWatch pages, straitmonitor.com files) are **not** redistributed here: each is listed by URL, hash and Wayback copy.
"Wayback (identical)" means the Wayback capture has the same content digest (SHA-1) as the bytes hashed here.
"Wayback (nearest)" means a capture of the same URL exists, but its content differs (live JSON/HTML changes over time).
"none found" means the Wayback CDX index had no 200 capture of that exact URL at the time of writing.

## PortWatch / ArcGIS (IMF PortWatch public API)

| Document | URL | SHA-256 | Wayback |
|---|---|---|---|
| Daily_Ports_Data layer metadata (committed: `metadata/layer_Daily_Ports_Data.json`) | https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Ports_Data/FeatureServer/0?f=json | `ff0ce1ec2bcb4c91a5ae559e98e784813fe563c4b1fd644826ae0eaad8156ffb` | none found |
| Daily_Chokepoints_Data layer metadata (committed: `metadata/layer_Daily_Chokepoints_Data.json`) | https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0?f=json | `bcaaf9409825bef07ef57723712aee003e187151e94ee8f9b76d6b53aa6da939` | nearest: https://web.archive.org/web/20261006121211/https://services9.arcgis.com/weJ1QsnbMYJlCHdG/arcgis/rest/services/Daily_Chokepoints_Data/FeatureServer/0?f=json |
| ArcGIS item, Daily_Ports_Data (field definitions in `description`) | https://www.arcgis.com/sharing/rest/content/items/83b1bbc7b3354c5fb1f40673bb8f852e?f=json | `c47b7e00b60d7b984d640ac138b2f29b3746b666282043c3da0a364dba954725` | none found |
| ArcGIS item, Daily_Chokepoints_Data (field definitions in `description`) | https://www.arcgis.com/sharing/rest/content/items/3da2b9ca97684916b75c4013f95d18ab?f=json | `08e00ca60b1663f46036ffabff2f87ac9668a0a4e7ba00ae4820928ab77b5e69` | nearest: https://web.archive.org/web/20260519165232/https://www.arcgis.com/sharing/rest/content/items/3da2b9ca97684916b75c4013f95d18ab?f=json |
| PortWatch "Data & Methodology" page content (incl. changelog), rendered at https://portwatch.imf.org/pages/data-and-methodology | https://www.arcgis.com/sharing/rest/content/items/19b92a4413c34407878791299acde8d7/data?f=json | `2aa6221077f068181b5d456413337257bceae7edbbde132f169a387b3a8e9568` | nearest (JSON): https://web.archive.org/web/20250515174911/https://www.arcgis.com/sharing/rest/content/items/19b92a4413c34407878791299acde8d7/data?f=json ; nearest (page): https://web.archive.org/web/20260915130134/https://portwatch.imf.org/pages/data-and-methodology |
| PortWatch "FAQs" page content, rendered at https://portwatch.imf.org/pages/faqs | https://www.arcgis.com/sharing/rest/content/items/640b69a4a96f41a6937cb4d2984f26da/data?f=json | `a4b3ce66a7dc7b4dce1a1894bd0eb0e85319b74830fff53c4de235e87ca06a24` | nearest (JSON): https://web.archive.org/web/20250515174931/https://www.arcgis.com/sharing/rest/content/items/640b69a4a96f41a6937cb4d2984f26da/data?f=json ; nearest (page): https://web.archive.org/web/20260915130133/https://portwatch.imf.org/pages/faqs |

Release identification: the layer metadata `editingInfo.lastEditDate` is 1791312087589 ms (2026-10-06 18:41 UTC) for
Daily_Ports_Data and 1791288541457 ms (2026-10-06 12:09 UTC) for Daily_Chokepoints_Data.

Raw PortWatch query responses used in Q2 are not shipped. Their names and SHA-256 are in
[q2/inputs_SHA256SUMS](q2/inputs_SHA256SUMS); the query URLs are those built by `../../scripts/get_data.py`
(AUDIT_END=2026-09-25). The live-API cross-check URLs and response hashes are in [q2/api/provenance.jsonl](q2/api/provenance.jsonl).

## IMF working papers

imf.org refused automated downloads at the time of this verification (HTTP "Access Denied"); both PDFs were obtained from
the Wayback captures below, whose digests are identical to the bytes hashed here.

| Document | URL | SHA-256 | Wayback |
|---|---|---|---|
| Arslanalp, S., Koepke, R., Verschuur, J. (2021). *Tracking Trade from Space: An Application to Pacific Island Countries*. IMF Working Paper WP/21/225 | https://www.imf.org/-/media/Files/Publications/WP/2021/English/wpiea2021225-print-pdf.ashx (landing page: https://www.imf.org/en/Publications/WP/Issues/2021/08/20/Tracking-Trade-from-Space-An-Application-to-Pacific-Island-Countries-464345) | `e5e07052f5722220581707fc2073a305280a092a1bfeaa8436da4cfcf9a8ef37` | identical: https://web.archive.org/web/20250317140718/https://www.imf.org/-/media/Files/Publications/WP/2021/English/wpiea2021225-print-pdf.ashx |
| Arslanalp, S., Choi, S. M., Kamali, P., Koepke, R., McKetty, M., Ruta, M., Saraiva, M., Sozzi, A., Verschuur, J. (2025). *Nowcasting Global Trade from Space*. IMF Working Paper WP/25/93 | https://www.imf.org/-/media/files/publications/wp/2025/english/wpiea2025093-print-pdf.pdf | `28ec6524760bdb266e4e605913b56b7592da7536a8e2502e0673220d18436673` | identical: https://web.archive.org/web/20260607053020/https://www.imf.org/-/media/files/publications/wp/2025/english/wpiea2025093-print-pdf.pdf |

## Third-party tracker (post 8, last clause)

| Document | URL | SHA-256 | Wayback |
|---|---|---|---|
| straitmonitor.com home page (label "Deadweight tonnage") | https://straitmonitor.com/ | `cf06d85b626824fc57813f80e2d147304212282895d25cde9ed0552d4ab37843` | nearest: https://web.archive.org/web/20260911122858/https://straitmonitor.com/ |
| straitmonitor.com app code (`capacity` field labelled `dwt`) | https://straitmonitor.com/app.js?v=10 | `8c9c2e405f232c6319cc00b48519205cbca92617a1aa8bcd4eed5f333c14da1d` | none found |
| straitmonitor.com data snapshot (`fetchedAt` 2026-10-07T20:35:02Z), compared in `q2/straitmonitor_check.txt` | https://straitmonitor.com/data/snapshot.js?v=202610072035 | `e01702ccfb9870a774bb44116577130a5d5e2c586c9183e0ae1c6840f1d16d3a` | none found |
