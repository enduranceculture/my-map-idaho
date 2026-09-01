# My Map — Idaho

Versioned geodata powering "my map" of Idaho. This repository is the reusable **geographic intelligence layer** for apps such as Ride Here and Forest Atlas. Consuming apps own their own cartography, terrain rendering, interaction, and UI.

## Base v1 status

**COMPLETE — 2026-09-01**

Base v1 establishes the easy, authoritative statewide geographic context needed before adding heavier thematic datasets or personal history. It includes land-management context, access, recreation, named hydrography, named landforms, and the existing forest / old-growth intelligence.

The visual basemap itself should still come from a mapping provider / map service. This repository should not become a dump of raster tiles, DEMs, or duplicate basemap geometry.

## Layers

| Layer | Status | Current source / scope | Files |
| --- | --- | --- | --- |
| Trails | **Live / regional packs** | USFS EDW National Forest System Trails | `data/trails/` |
| Idaho state / USFS boundaries | **Live statewide** | US Census Bureau + USFS EDW | `data/boundaries/` |
| Public-land managers | **Live statewide** | USGS PAD-US 4.1 fee/public-land manager view | `data/boundaries/` |
| Ranger Districts | **Live statewide** | USFS EDW Ranger District Boundaries | `data/boundaries/` |
| Drive-access roads | **Live statewide** | USFS National Forest System Roads | `data/access/` |
| Recreation / trailheads | **Live statewide** | USFS Recreation Opportunities + Recreation Infrastructure | `data/access/` |
| Named hydrography | **Live statewide** | USGS 3D Hydrography Program (3DHP) | `data/hydro/` |
| Named physical landforms | **Live statewide** | USGS GNIS / The National Map Gazetteer | `data/places/` |
| Old-growth research points | **Live** | Researched onX waypoints accepted for this map | `data/old-growth/` |
| Mature / old-growth landscape inventory | **Live statewide** | USDA Forest Service Fireshed Mature and Old Growth Area | `data/old-growth/` |
| Rockhounding | **Partial / live** | Researched onX point(s); thematic enrichment later | `data/rockhounding/` |
| Ride history | **Deferred** | Strava / GPX activity history | future `data/ride-history/` |
| Trees / vegetation | Future thematic expansion | USFS FSVeg / LANDFIRE / other validated sources | `data/trees/` |

## Base v1 snapshot

Current authoritative / derived feature counts:

| Intelligence | Features |
| --- | ---: |
| Census Idaho boundary | 1 |
| USFS Administrative Forest records | 17 |
| USFS Wilderness records | 9 |
| USFS Ranger District records | 58 |
| PAD-US public-land manager polygons | 1,685 |
| USFS drive-access road segments | 9,510 |
| USFS Recreation Opportunities areas | 987 |
| Recreation Opportunities trailhead derivative | 256 |
| USFS rich Recreation Infrastructure sites | 4,338 |
| Rich recreation trailhead derivative | 488 |
| USGS 3DHP named flowlines | 115,879 |
| USGS 3DHP named waterbodies | 1,907 |
| USGS 3DHP springs | 12,836 |
| USGS GNIS physical landforms | 8,374 |
| Researched old-growth / ancient-tree points | 15 |
| USDA Mature / Old-Growth Fireshed features | 188 |

Counts reflect the 2026-09-01 snapshot and can change when authoritative upstream sources change.

## Source-of-truth rule

Keep source classes separate rather than merging them into one ambiguous dataset:

- official / institutional GIS data;
- user-researched points explicitly accepted for this personal map;
- personal activity history when added later;
- derived lightweight map-facing versions of the above.

Placeholder or illustrative geometry should never be promoted as source truth. App styling, labels, opacity, colors, layer priority, terrain, hillshade, and interaction belong to the consuming app.

## Large-layer packaging

GitHub has practical single-file limits, while statewide source geometry can be large. We preserve the full logical dataset rather than deleting detail just to fit one file.

When a generated GeoJSON exceeds the repository packaging threshold, `scripts/package_large_geojson.py` writes:

- a `*_manifest.json` file;
- deterministic `*_part001.geojson`, `*_part002.geojson`, ... shards.

Load **every shard listed in the manifest** as one logical layer. Shard boundaries have no geographic meaning.

Current sharded logical layers:

- `data/access/usfs_roads_idaho_manifest.json` — **9,510** road features across **2** source-faithful shards. The lighter `usfs_roads_idaho_map.geojson` remains a single browser-facing file.
- `data/hydro/usgs_3dhp_named_flowlines_idaho_manifest.json` — **115,879** flowline features across **6** source-faithful shards.
- `data/hydro/usgs_3dhp_named_flowlines_idaho_map_manifest.json` — the same **115,879** flowlines across **4** simplified map-facing shards.

## Current trail packs

Trail coverage is intentionally independent from the statewide Base v1 context. Current USFS packs include:

- Wood River / Sawtooth: `usfs_trails_woodriver_sawtooth.geojson` plus bike and map-facing derivatives.
- Warm Springs / Bonneville: `usfs_trails_warm_springs_bonneville.geojson` plus bike and map-facing derivatives.

`bike_status=unknown` means the published USFS bicycle fields are blank. It does **not** mean bicycles are prohibited.

## Old-growth interpretation

`data/old-growth/` contains two complementary forms of intelligence:

- researched waypoints for notable old-growth / ancient-tree locations and related context;
- USDA Fireshed mature / old-growth landscape inventory polygons.

The USDA Fireshed polygons are landscape-scale inventory/context, not stand-level or individual-tree locations. Keep them visually and semantically separate from researched points.

## Refresh automation

- `.github/workflows/refresh-trails.yml` — regional USFS trail data.
- `.github/workflows/refresh-foundation.yml` — Census Idaho boundary, USFS forest/wilderness boundaries, USDA mature-old-growth context.
- `.github/workflows/refresh-access-hydro-names.yml` — statewide USFS access/recreation, USGS 3DHP hydrography, and GNIS landforms; scheduled after the foundation refresh.
- `.github/workflows/refresh-base-v1.yml` — PAD-US public-land managers, USFS Ranger Districts, and rich recreation infrastructure; scheduled after the other Base v1 refreshers.

Generated geometry is clipped locally against the versioned Census Idaho boundary where appropriate. Refreshers rebase before push so independently scheduled map-data jobs can coexist.

## Using in an app

Simple map-facing layers can be consumed directly from raw GitHub URLs. For example:

```js
map.addSource("usfs-roads", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/access/usfs_roads_idaho_map.geojson",
});

map.addSource("public-land-managers", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/boundaries/usgs_padus4_1_public_land_managers_idaho_map.geojson",
});

map.addSource("recreation-sites", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/access/usfs_recreation_sites_rich_idaho_map.geojson",
});

map.addSource("old-growth-research", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/old-growth/old_growth_research_points_idaho.geojson",
});
```

For a sharded layer such as statewide named flowlines, fetch its manifest and load every listed shard as the same logical map layer.

The repository is public, so raw GitHub data URLs can be consumed by browser apps without embedding a GitHub access token.
