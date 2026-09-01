# Hydrography layers

Hydro intelligence comes from the **USGS 3D Hydrography Program (3DHP)** service in The National Map. 3DHP is the successor-direction hydrography framework and combines elevation-derived hydrography where available with NHD-derived coverage elsewhere.

The goal here is not to duplicate every tiny water line already present in a basemap. These layers add named, queryable geographic intelligence.

## Named flowlines

- `usgs_3dhp_named_flowlines_idaho.geojson` — Idaho-clipped named flowlines with source geometry and useful 3DHP attributes.
- `usgs_3dhp_named_flowlines_idaho_map.geojson` — lighter geometry for browser rendering.

Useful fields include `gnisid`, `gnisidlabel`, feature type, flow direction, stream level/order and 3DHP identifiers.

## Named waterbodies

- `usgs_3dhp_named_waterbodies_idaho.geojson`
- `usgs_3dhp_named_waterbodies_idaho_map.geojson`

Includes named 3DHP lakes, rivers and other published waterbody polygons intersecting Idaho.

## Springs

`usgs_3dhp_springs_idaho.geojson`

3DHP HydroLocation records whose published feature type is `Spring`. Some springs have GNIS names and some do not. Keep unnamed records rather than pretending an unnamed spring does not exist.

## Interpretation

These datasets are strong geographic context, not a guarantee of current water availability, flow, water quality, legal access, or drinking-water safety. Apps should keep that distinction explicit.
