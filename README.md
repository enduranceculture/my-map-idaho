# My Map — Idaho

Versioned geodata powering "my map" of Idaho. Topical intelligence lives here as independent GeoJSON/data layers with explicit provenance; apps such as Ride Here and Forest Atlas consume the layers by URL and own their own cartography/UI.

## Layers

| Layer | Status | Source | Files |
| --- | --- | --- | --- |
| Trails (USFS) | Live | USFS EDW National Forest System Trails | `data/trails/` |
| Old-growth research | **Live** | Nick's researched onX waypoints; USDA source definition staged separately | `data/old-growth/` |
| Rockhounding | **Partial / live** | Nick's researched onX point(s); IGS / USGS / vetted Mindat enrichment planned | `data/rockhounding/` |
| Trees / vegetation | Planned | USFS FSVeg / LANDFIRE / other validated vegetation sources | `data/trees/` |

## Source-of-truth rule

This repository should contain geographic intelligence, not app-specific styling. Keep source classes separate rather than merging them into one ambiguous dataset:

- official / institutional GIS data
- user-researched points accepted for this personal map
- personal activity history (future private layer)
- app presentation / basemap styling (owned by the consuming app)

Placeholder or illustrative geometry should not be promoted as source truth.

## Trails layer

- `usfs_trails_woodriver_sawtooth.geojson` — full USFS source layer for the Wood River / Sawtooth bounding box (-115.2, 43.3 → -114.0, 44.3). Preserve as source truth.
- `usfs_bike_trails_woodriver_sawtooth.geojson` — subset whose published USFS bicycle fields explicitly confirm bicycle use.
- `usfs_trails_woodriver_sawtooth_map.geojson` — lightweight app-facing version of the complete trail network, simplified to roughly 4 m tolerance with normalized stable IDs and bicycle status.

The app-facing layer adds:

- `trail_id`
- `segment_id`
- `bike_status` — `confirmed`, `restricted`, `discouraged`, or `unknown`
- `bike_season` / `bike_restricted_season`
- explicit `source` provenance

`bike_status=unknown` means the published USFS bicycle fields are blank. It does **not** mean bicycles are prohibited.

## Old-growth research layer

`data/old-growth/old_growth_research_points_idaho.geojson` contains the 2026-08-31 onX old-growth / ancient-tree research export, normalized into a map-ready FeatureCollection while preserving source-level precision caveats.

The collection deliberately distinguishes strict old-growth / ancient-tree records from mature-forest, riparian, ecological, and cultural context using `strict_old_growth` and `old_growth_relevance`.

The unrelated `GEODES!` waypoint found in that same onX export was routed to the rockhounding layer instead of contaminating old-growth data.

Forest Atlas V2 also identified the official USDA Fireshed Mature and Old Growth layer. Its source definition is preserved in `data/old-growth/usda_fireshed_source.json`; the polygon snapshot is not yet materialized because the previous upstream ArcGIS ingestion failed closed rather than accepting incomplete data.

## Refresh

`.github/workflows/refresh-trails.yml` re-pulls the USFS trail layer on the first of every month (and on demand) and commits only when data changes.

To expand trail coverage, add a bbox to `REGIONS` in `scripts/pull_usfs_trails.py`.

## Using in an app (Mapbox GL)

```js
map.addSource("usfs-trails", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/trails/usfs_trails_woodriver_sawtooth_map.geojson",
});

map.addSource("old-growth-research", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/old-growth/old_growth_research_points_idaho.geojson",
});
```

The repository is public, so these raw GitHub URLs can be consumed by browser apps without embedding a GitHub access token.
