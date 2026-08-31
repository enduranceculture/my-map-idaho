# My Map — Idaho

Versioned geodata powering "my map" of Idaho: every topical layer (trails, rockhounding, trees, and whatever comes next) lives here as GeoJSON, with provenance and automated refresh. Apps (Ride Here and others) consume these files by URL — this repo never touches app code.

## Layers

| Layer | Status | Source | Files |
| --- | --- | --- | --- |
| Trails (USFS) | Live | [USFS EDW National Forest System Trails](https://data.fs.usda.gov/geodata/edw/datasets.php?xmlKeyword=trailnfs) — public domain, USFS updates daily | `data/trails/` |
| Rockhounding | Planned | IGS DD-1, USGS MRDS, Mindat (see the Idaho Rockhounding Source Library in Notion) | `data/rockhounding/` |
| Trees / vegetation | Planned | USFS FSVeg / LANDFIRE / iNaturalist — TBD | `data/trees/` |

## Trails layer

- `usfs_trails_woodriver_sawtooth.geojson` — the full USFS source layer for the Wood River / Sawtooth bounding box (-115.2, 43.3 → -114.0, 44.3). Preserve this as source truth.
- `usfs_bike_trails_woodriver_sawtooth.geojson` — the subset whose USFS bicycle management/accepted fields explicitly confirm bicycle use.
- `usfs_trails_woodriver_sawtooth_map.geojson` — lightweight app-facing version of the full network. It retains every source feature, simplifies geometry to roughly 4 m tolerance, and normalizes stable identifiers plus bicycle status for fast map rendering.

Raw trail features include USFS `trail_cn`, `objectid`, name/number, class, mileage, surface, grade/tread fields, bicycle/e-bike/moto season fields, and managing org. The app-facing layer adds:

- `trail_id` — `usfs:<trail_cn>` when available, otherwise a source fallback
- `segment_id` — source record identifier using USFS `objectid`
- `bike_status` — `confirmed`, `restricted`, `discouraged`, or `unknown`
- `bike_season` / `bike_restricted_season`
- `source` — explicit provenance

Important: `bike_status=unknown` means the published USFS bicycle fields are blank. It does **not** mean bicycles are prohibited. Apps should render unknown-access trail data distinctly rather than silently treating it as bike-legal or bike-illegal.

## Refresh

`.github/workflows/refresh-trails.yml` re-pulls from the USFS live endpoint on the 1st of every month (or on demand via the Actions tab) and commits only when data actually changed — so the commit history doubles as a change log of trail network updates. A change to the pull script on `main` also refreshes once so new derived layers are materialized immediately.

To expand coverage, add a bbox to `REGIONS` in `scripts/pull_usfs_trails.py`.

## Using in an app (Mapbox GL / Lovable)

Prefer the app-facing all-trails layer so the map can show the complete network while preserving access confidence:

```js
map.addSource("usfs-trails", {
  type: "geojson",
  data: "https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/trails/usfs_trails_woodriver_sawtooth_map.geojson",
});
```

The raw URL works without credentials only when this repository/data endpoint is public. While the repo is private, apps must use a server-side authenticated proxy or another explicitly approved public delivery path; never put a GitHub access token in browser code.
