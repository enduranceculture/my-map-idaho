# My Map — Idaho

Versioned geodata powering "my map" of Idaho: every topical layer (trails, rockhounding, trees, and whatever comes next) lives here as GeoJSON, with provenance and automated refresh. Apps (Ride Here and others) consume these files by URL — this repo never touches app code.

## Layers

| Layer | Status | Source | Files |
| --- | --- | --- | --- |
| Trails (USFS) | Live | [USFS EDW National Forest System Trails](https://data.fs.usda.gov/geodata/edw/datasets.php?xmlKeyword=trailnfs) — public domain, USFS updates daily | `data/trails/` |
| Rockhounding | Planned | IGS DD-1, USGS MRDS, Mindat (see the Idaho Rockhounding Source Library in Notion) | `data/rockhounding/` |
| Trees / vegetation | Planned | USFS FSVeg / LANDFIRE / iNaturalist — TBD | `data/trees/` |

## Trails layer

- `usfs_trails_woodriver_sawtooth.geojson` — all 855 USFS trail segments (~2,145 mi) in the Wood River / Sawtooth bounding box (-115.2, 43.3 → -114.0, 44.3)
- `usfs_bike_trails_woodriver_sawtooth.geojson` — the 220 segments (~674 mi, 158 named trails) managed or accepted for bicycles

Every feature is a WGS84 LineString with: `trail_name`, `trail_no`, `trail_class`, `gis_miles`, `trail_surface`, `typical_trail_grade`, `typical_tread_width`, bike/e-bike/moto season fields, and managing org.

## Refresh

`.github/workflows/refresh-trails.yml` re-pulls from the USFS live endpoint on the 1st of every month (or on demand via the Actions tab) and commits only when data actually changed — so the commit history doubles as a change log of trail network updates.

To expand coverage, add a bbox to `REGIONS` in `scripts/pull_usfs_trails.py`.

## Using in an app (Mapbox GL / Lovable)

```js
map.addSource('bike-trails', {
  type: 'geojson',
  data: 'https://raw.githubusercontent.com/<owner>/my-map-idaho/main/data/trails/usfs_bike_trails_woodriver_sawtooth.geojson'
});
map.addLayer({ id: 'bike-trails', type: 'line', source: 'bike-trails' });
```

Note: raw URLs require the repo to be public (or a token if private). All data here is public-domain government data.
