# Access layers

Authoritative access and recreation intelligence for Idaho. These files sit above a visual basemap; they do not replace one.

## USFS drive-access roads

Current snapshot: **9,510 Idaho-clipped road segments**.

Source: USFS Enterprise Data Warehouse — National Forest System Roads.

The Base v1 road scope intentionally keeps the published USFS symbol classes representing paved, gravel, and dirt passenger-car roads plus roads not maintained for passenger cars. This is more useful to map consumers than carrying every administrative road record.

### Files

- `usfs_roads_idaho_manifest.json` — canonical manifest for the source-faithful logical layer. The 9,510 records are split across 2 GeoJSON shards to stay below GitHub file limits.
- `usfs_roads_idaho_part001.geojson`
- `usfs_roads_idaho_part002.geojson`
- `usfs_roads_idaho_map.geojson` — single lighter browser-facing file, simplified by roughly 3–4 m.

When source-faithful road geometry is required, load **both shards listed in the manifest**. Shard boundaries have no geographic meaning.

Useful fields include road name/ID, surface, maintenance level, functional class, route status, jurisdiction, managing organization and published `openforuseto` information.

Derived `access_class` is intentionally simple:

- `passenger-car` — USFS published road symbol indicates paved/gravel/dirt suitable for passenger cars.
- `high-clearance-or-rough` — USFS symbol indicates road not maintained for passenger cars.
- `unknown` — do not infer suitability.

This is **not** a guarantee that a road is currently open, snow-free, legally drivable, or passable. Current conditions/closure data should remain a separate live concern.

## USFS Recreation Opportunities

Current snapshot: **987 recreation areas**, with a **256-feature trailhead derivative**.

- `usfs_recreation_opportunities_idaho.geojson`
- `usfs_trailheads_idaho.geojson`

The Recreation Opportunities feed can publish multiple activity rows for one recreation area, so this repository consolidates those rows into one feature per `RECAREAID` with activities grouped together.

The trailhead file is a convenient derivative whose name or published activity contains `Trailhead`. It is not an exhaustive inventory of informal parking/access points.

## USFS rich Recreation Infrastructure

Current snapshot: **4,338 recreation infrastructure sites**, with a **488-feature trailhead derivative**.

- `usfs_recreation_sites_rich_idaho.geojson` — source-rich statewide site records.
- `usfs_recreation_sites_rich_idaho_map.geojson` — lighter property set for app delivery.
- `usfs_trailheads_rich_idaho.geojson` — sites whose published `site_type` contains `TRAILHEAD`.

This source adds the richer practical context that the simpler Recreation Opportunities feed does not consistently expose, including published activity/service lists, seasonal operational status, fees, open season, usage level, water/restroom availability, permits, restrictions, directions, elevations, capacity and official URLs when present.

## Refresh

- `.github/workflows/refresh-access-hydro-names.yml` rebuilds drive-access roads plus the Recreation Opportunities layer.
- `.github/workflows/refresh-base-v1.yml` rebuilds the richer Recreation Infrastructure layer.
- `scripts/package_large_geojson.py` shards oversized logical source layers without dropping features.

All statewide data is clipped/filtered for Idaho using the repository's Census state geometry and authoritative source coordinates.
