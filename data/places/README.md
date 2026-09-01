# Named geographic features

## USGS GNIS physical landforms

`usgs_gnis_landforms_idaho.geojson`

Current snapshot: **8,374 Idaho physical-landform features**.

Source: **USGS Geographic Names Information System (GNIS) / The National Map Gazetteer**.

GNIS is the federal/national standard for geographic nomenclature. This layer gives consuming apps stable names and IDs for physical features such as summits, gaps/passes, valleys, canyons, ridges and other named landforms without depending on whatever label set a visual basemap happens to show at a given zoom level.

Useful fields include:

- `place_id` — normalized `gnis:<gaz_id>` identifier.
- `name` / `gaz_name` — published geographic name.
- `feature_class` / `gaz_featureclass` — GNIS feature class.
- county/state fields.
- `gaz_id` — GNIS/Gazetteer feature identifier.
- `isunknowncoords` — preserve the upstream coordinate-status signal rather than silently treating every point as surveyed precision.

The layer intentionally focuses on **physical landforms**. It does not try to duplicate every populated-place, structure, business or road label already supplied by a basemap.

## Refresh

`.github/workflows/refresh-access-hydro-names.yml` rebuilds the GNIS landform layer from the authoritative service and filters it to Idaho.
