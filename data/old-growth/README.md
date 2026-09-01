# Old-growth / mature-forest intelligence

This layer is intentionally separate from the general `trees/` layer. It combines two different kinds of intelligence that should remain distinguishable in consuming apps:

1. **researched point locations** — Nick's onX old-growth / ancient-tree research;
2. **official landscape inventory** — USDA Forest Service mature / old-growth Fireshed polygons.

## Live personal research

`old_growth_research_points_idaho.geojson` contains 15 Idaho waypoints researched by Nick and exported from onX Backcountry on 2026-08-31.

For this personal map, these points are accepted as authoritative user research. That does **not** mean every marker is a surveyed individual tree or a formally mapped old-growth polygon. Source-level precision caveats remain attached to each feature.

Useful fields:

- `old_growth_relevance` — old-growth, mature-old-growth, ancient-tree-site, historic-old-tree-site, or a context classification.
- `strict_old_growth` — `true` for records intended to behave as old-growth / ancient-tree records; `false` for mature forest, ecological, riparian, or cultural context saved during the same research.
- `species`, `age`, `confidence`, `access` — normalized from the research notes where present.
- `summary` — compact map-facing description.
- `position_status` — marks source notes that explicitly warn the position is approximate/imprecise.
- `source`, `source_file`, `source_export_date` — provenance back to the onX export.

The source GPX included one unrelated `GEODES!` waypoint. It is intentionally **not** in this layer; it lives in `data/rockhounding/onx_rockhounding_research_points_idaho.geojson` instead.

## Live USDA mature / old-growth inventory

The official USDA Forest Service Fireshed Mature and Old Growth layer is now materialized for Idaho.

- **Source layer:** Fireshed Mature and Old Growth Area, Federal Lands Only (polygon)
- **ArcGIS MapServer layer:** `WO_OSC_GapAnalysis_OldGrowthAndMatureForests/MapServer/29`
- **Current Idaho-clipped features:** 188
- **Key fields:** `MATURE_ACRES`, `OLD_GROWTH_ACRES`, `ForestType`, `Division`, `Fireshed_Name`, `Nine_Class`, and source uncertainty fields.

Files:

- `usda_mature_old_growth_firesheds_idaho.geojson` — source-faithful geometry clipped exactly to the Census Idaho boundary.
- `usda_mature_old_growth_firesheds_idaho_map.geojson` — topology-preserving simplified version for browser rendering.
- `usda_fireshed_source.json` — durable source definition and provenance notes.

### Important interpretation

The USDA Fireshed dataset is **landscape-scale inventory/context**, not a stand-by-stand map of exact ancient trees. A polygon means the authoritative source reports mature / old-growth estimates and classification for that Fireshed geography on federal lands. It should complement—not replace—the researched point layer.

The ingestion deliberately avoids depending on the flaky spatial-query behavior previously encountered in Forest Atlas V2. It uses the companion USDA Fireshed boundary layer to identify candidate Firesheds touching Idaho, requests layer 29 by authoritative `Fireshed_Name`, and then clips locally to the Census Idaho boundary. Full national pagination remains a fallback.

## Refresh

`scripts/pull_idaho_foundation.py` rebuilds the USDA polygon layer. `.github/workflows/refresh-foundation.yml` runs monthly and can be launched manually.

## What was deliberately not copied from Forest Atlas V2

The bundled Forest Atlas Idaho waypoint fixtures and hand-authored forest-context polygons are not promoted into this repository. Their own source files label them as placeholder / stylized data rather than surveyed GIS truth.
