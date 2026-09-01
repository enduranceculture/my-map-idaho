# Old-growth research layer

This layer is intentionally separate from the general `trees/` layer.

## Live personal research

`old_growth_research_points_idaho.geojson` contains 15 Idaho waypoints researched by Nick and exported from onX Backcountry on 2026-08-31.

For this personal map, these points are accepted as authoritative user research. That does **not** mean every marker is a surveyed individual tree or a formally mapped old-growth polygon. The source-level precision caveats remain attached to each feature.

Useful fields:

- `old_growth_relevance` — old-growth, mature-old-growth, ancient-tree-site, historic-old-tree-site, or a context classification.
- `strict_old_growth` — `true` for records intended to behave as old-growth / ancient-tree records; `false` for mature forest, ecological, riparian, or cultural context saved during the same research.
- `species`, `age`, `confidence`, `access` — normalized from the research notes where present.
- `summary` — compact map-facing description.
- `position_status` — marks source notes that explicitly warn the position is approximate/imprecise.
- `source`, `source_file`, `source_export_date` — provenance back to the onX export.

The source GPX included one unrelated `GEODES!` waypoint. It is intentionally **not** in this layer; it lives in `data/rockhounding/onx_rockhounding_research_points_idaho.geojson` instead.

## USDA mature / old-growth inventory

Forest Atlas V2 identified the official USDA Forest Service layer:

- **Layer:** Fireshed Mature and Old Growth Area, Federal Lands Only (polygon)
- **ArcGIS MapServer layer:** `WO_OSC_GapAnalysis_OldGrowthAndMatureForests/MapServer/29`
- **Key fields:** mature acres, old-growth acres, forest type, division, fireshed, and the USDA nine-class mature/old-growth classification.

The previous Forest Atlas sync correctly failed closed when the USDA service rejected its spatial / ID queries, so no empty or fabricated polygon layer is promoted here. `usda_fireshed_source.json` preserves the authoritative source definition for the next ingestion pass.

## What was deliberately not copied from Forest Atlas V2

The bundled Forest Atlas Idaho waypoint fixtures and hand-authored forest-context polygons are not promoted into this repository. Their own source files label them as placeholder / stylized data rather than surveyed GIS truth.
