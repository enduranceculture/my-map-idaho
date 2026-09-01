# Hydrography layers

Hydro intelligence comes from the **USGS 3D Hydrography Program (3DHP)** service in The National Map. These layers add named/queryable geographic intelligence rather than duplicating every tiny water line already rendered by a basemap.

## Named flowlines

Current snapshot: **115,879 Idaho-clipped named flowline features**.

The logical source and map-facing datasets are large enough that each is stored as deterministic GeoJSON shards:

- `usgs_3dhp_named_flowlines_idaho_manifest.json` — canonical source-faithful manifest; **6 shards** total.
- `usgs_3dhp_named_flowlines_idaho_part001.geojson` through `part006.geojson` — source-faithful geometry/attributes.
- `usgs_3dhp_named_flowlines_idaho_map_manifest.json` — canonical simplified map-facing manifest; **4 shards** total.
- `usgs_3dhp_named_flowlines_idaho_map_part001.geojson` through `part004.geojson` — simplified geometry for app rendering.

Load **every shard listed in the relevant manifest** as one logical layer. Shard boundaries are packaging only and have no geographic meaning.

Useful fields include 3DHP identifiers, GNIS ID/name, feature type, flow direction, stream level/order and work-unit identifiers.

## Named waterbodies

Current snapshot: **1,907 features**.

- `usgs_3dhp_named_waterbodies_idaho.geojson` — source geometry/attributes.
- `usgs_3dhp_named_waterbodies_idaho_map.geojson` — lighter browser-facing geometry.

Includes named 3DHP waterbody polygons intersecting Idaho.

## Springs

Current snapshot: **12,836 features**.

- `usgs_3dhp_springs_idaho.geojson`

This layer retains 3DHP spring HydroLocation records in Idaho. Some have GNIS names and some do not; unnamed records remain because an absent name does not mean an absent spring.

## Interpretation

These datasets are strong geographic context, not guarantees of current flow, water availability, water quality, legal access, or drinking-water safety. Those time-sensitive questions should be handled separately from this versioned base layer.

## Refresh

`.github/workflows/refresh-access-hydro-names.yml` rebuilds the statewide hydro layers. The source query is spatially prefiltered and the final geometry is clipped locally to the Census Idaho boundary. `scripts/package_large_geojson.py` automatically shards oversized logical layers without discarding features.
