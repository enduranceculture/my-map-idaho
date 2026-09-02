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

## Curated mountain-range labels

`idaho_mountain_range_labels_v1.geojson`

This lightweight 19-feature derivative turns a deliberately selected subset of official GNIS Range records into useful statewide, regional, and Ketchum-area map labels. It also retains three immediate border-context ranges—the Teton, Snake River, and Cabinet ranges—without classifying them as wholly inside Idaho.

The point geometry is a **cartographic anchor**, not a range boundary. Most anchors are the mean of the published GNIS multipoints; single-point records retain the published feature location. `label_tier` is a visual hierarchy only and does not invent parent/sub-range relationships that GNIS does not supply.

Local display conventions remain explicit and reversible:

- `Smoky Mountains` retains the owner-confirmed alias `The Smokies`.
- `White Cloud Peaks` is the official GNIS name; the map-facing name `White Clouds` is also supported by USDA Forest Service usage.
- Other colloquial plurals are stored as aliases while map titles retain their official names.

## Refresh

`.github/workflows/refresh-access-hydro-names.yml` rebuilds the GNIS landform layer from the authoritative service and filters it to Idaho.

The curated range-label derivative is intentionally not overwritten by that broad refresh. Changes to its membership, label tier, or anchor require review.
