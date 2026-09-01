# Named geographic features

`usgs_gnis_landforms_idaho.geojson`

Authoritative physical-feature names from the **USGS Geographic Names Information System (GNIS) / The National Map Gazetteer**, filtered to Idaho and clipped to the Census state boundary.

GNIS is the federal and national standard for geographic nomenclature. This landform layer is intended to give consuming apps stable names and IDs for features such as summits, gaps/passes, valleys, canyons, ridges and other named physical landforms without depending on whatever label set a basemap happens to show at a given zoom level.

Useful fields:

- `place_id` — normalized `gnis:<gaz_id>` identifier.
- `name` / `gaz_name` — federally recognized geographic name.
- `feature_class` / `gaz_featureclass` — GNIS feature class.
- `county_name` and `state_alpha`.
- `gaz_id` — permanent GNIS/Gazetteer feature identifier.
- `isunknowncoords` — preserve the upstream coordinate-status signal rather than silently treating every point as surveyed precision.

This layer intentionally focuses on **physical landforms**. Populated places, structures and roads remain separate concerns and can be added later if they become valuable to the product.
