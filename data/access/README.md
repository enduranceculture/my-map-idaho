# Access layers

Authoritative access intelligence for Idaho. These files are intended to sit above a visual basemap, not replace it.

## USFS roads

`usfs_roads_idaho_map.geojson`

- Source: USFS Enterprise Data Warehouse — National Forest System Roads.
- Scope: every source road segment intersecting Idaho, clipped to the Census Idaho boundary.
- Geometry is simplified by roughly 3–4 m for browser delivery; source road attributes are retained.
- Useful fields include road name/ID, surface, maintenance level, functional class, route status, jurisdiction, managing organization and published `openforuseto` information.
- Derived `access_class` is intentionally simple:
  - `passenger-car` — USFS published road symbol indicates paved/gravel/dirt suitable for passenger cars.
  - `high-clearance-or-rough` — USFS symbol indicates road not maintained for passenger cars.
  - `unknown` — do not infer suitability.

This is **not** a guarantee that a road is currently open, snow-free, legally drivable, or passable. Apps should combine it with current closures/conditions when those sources are available.

## USFS recreation opportunities

`usfs_recreation_opportunities_idaho.geojson`

The Forest Service Recreation Opportunities feed is published for public use and refreshed nightly upstream. The source can contain multiple activity rows for one recreation area, so this repository consolidates those rows into one feature per `RECAREAID` with an `activities` array.

`usfs_trailheads_idaho.geojson`

A convenient derivative of the recreation layer whose name or published activity contains `Trailhead`. It is useful for map access points but should not be interpreted as an exhaustive list of every informal parking area or trail access location in Idaho.
