# My Map — Idaho

Versioned geodata powering "my map" of Idaho. Topical intelligence lives here as independent GeoJSON/data layers with explicit provenance; apps such as Ride Here and Forest Atlas consume the layers by URL and own their own cartography/UI.

## Layers

| Layer | Status | Source | Files |
| --- | --- | --- | --- |
| Trails | **Live** | USFS EDW National Forest System Trails | `data/trails/` |
| Idaho / land-management boundaries | **Live** | US Census Bureau + USFS EDW | `data/boundaries/` |
| Old-growth research points | **Live** | Nick's researched onX waypoints | `data/old-growth/` |
| Mature / old-growth landscape inventory | **Live** | USDA Forest Service Fireshed Mature and Old Growth Area | `data/old-growth/` |
| Rockhounding | **Partial / live** | Nick's researched onX point(s); IGS / USGS / vetted Mindat enrichment planned | `data/rockhounding/` |
| Ride history | Planned | Nick's Strava / GPX activity history; public layer is acceptable | future `data/ride-history/` |
| Trees / vegetation | Planned | USFS FSVeg / LANDFIRE / other validated vegetation sources | `data/trees/` |

## Source-of-truth rule

This repository contains geographic intelligence, not app-specific styling. Keep source classes separate rather than merging them into one ambiguous dataset:

- official / institutional GIS data;
- user-researched points accepted for this personal map;
- personal activity history;
- derived lightweight map-facing versions of the above.

Placeholder or illustrative geometry should not be promoted as source truth. Basemap styling, terrain presentation, labels, colors, and interaction belong to the consuming app.

## Current Idaho foundation

`data/boundaries/` now provides:

- exact Idaho state geometry from the **US Census Bureau 2025 Cartographic Boundary Files**;
- **17** Idaho-clipped USFS Administrative Forest records;
- **9** Idaho-clipped USFS National Wilderness records;
- source-faithful and lighter `_map.geojson` versions where appropriate.

`data/old-growth/` now provides two complementary old-growth views:

- **15 researched onX waypoints** for notable old-growth / ancient-tree and related forest context;
- **188 USDA Mature / Old-Growth Fireshed features** clipped to Idaho.

The USDA Fireshed polygons are landscape-scale inventory/context, not stand-level or individual-tree locations. They should be rendered as a separate layer from the researched point collection.

## Trails layer

- `usfs_trails_woodriver_sawtooth.geojson` — full USFS source layer for the Wood River / Sawtooth bounding box. Preserve as source truth.
- `usfs_bike_trails_woodriver_sawtooth.geojson` — subset whose published USFS bicycle fields explicitly confirm bicycle use.
- `usfs_trails_woodriver_sawtooth_map.geojson` — lightweight app-facing version of the complete trail network with normalized IDs and bicycle status.

`bike_status=unknown` means the published USFS bicycle fields are blank. It does **not** mean bicycles are prohibited.

## Refresh

- `.github/workflows/refresh-trails.yml` refreshes the USFS trail layer monthly and on demand.
- `.github/workflows/refresh-foundation.yml` refreshes Idaho boundary / forest / wilderness context plus USDA mature-old-growth inventory monthly and on demand.
- `scripts/pull_idaho_foundation.py` clips authoritative polygon sources locally against the Census Idaho boundary and generates lighter map-facing derivatives.

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

map.addSource("old-growth-firesheds", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/old-growth/usda_mature_old_growth_firesheds_idaho_map.geojson",
});

map.addSource("wilderness", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/boundaries/usfs_wilderness_idaho_map.geojson",
});
```

The repository is public, so these raw GitHub URLs can be consumed by browser apps without embedding a GitHub access token.
