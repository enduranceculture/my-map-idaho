# Idaho boundary / land-management context

Authoritative Idaho context for state extent, public-land management, National Forest administration, Ranger Districts, and Wilderness.

## Live files

| File | Current features | Source | Use |
| --- | ---: | --- | --- |
| `idaho_census_2025.geojson` | 1 | US Census Bureau 2025 Cartographic Boundary Files, States, 1:500,000 | Exact Idaho clipping / outline |
| `usfs_administrative_forests_idaho.geojson` | 17 | USFS EDW Administrative Forest Boundaries | Source-faithful Idaho-clipped National Forest geometry |
| `usfs_administrative_forests_idaho_map.geojson` | 17 | Derived from source-faithful forest geometry | Lighter browser/map rendering |
| `usfs_wilderness_idaho.geojson` | 9 | USFS EDW National Wilderness Areas | Source-faithful Idaho-clipped Wilderness geometry |
| `usfs_wilderness_idaho_map.geojson` | 9 | Derived from source-faithful Wilderness geometry | Lighter browser/map rendering |
| `usfs_ranger_districts_idaho.geojson` | 58 | USFS EDW Ranger District Boundaries | Source-faithful current Ranger District geometry intersecting Idaho |
| `usfs_ranger_districts_idaho_map.geojson` | 58 | Derived from Ranger District source geometry | Lighter district context for apps |
| `usgs_padus4_1_public_land_managers_idaho.geojson` | 1,685 | USGS PAD-US 4.1 Fee Managers | Source-rich public/protected-land manager geometry clipped to Idaho |
| `usgs_padus4_1_public_land_managers_idaho_map.geojson` | 1,685 | Derived from PAD-US 4.1 manager geometry | Lighter browser-facing land-manager layer |

Feature counts are for the 2026-09-01 Base v1 snapshot and can change when authoritative upstream data changes.

## PAD-US public-land manager layer

The Base v1 PAD-US layer uses the **PAD-US 4.1 Fee Managers** view to answer a practical map question: **who owns/manages this public or protected land?** It is not intended to reproduce every overlapping conservation designation in PAD-US.

For this base layer, manager types representing federal, Tribal, state, local, district, joint, and territorial management are retained. Private, NGO, and unknown manager types are excluded from this particular public-land-manager derivative rather than being mislabeled as public land.

Useful source fields include ownership/manager type and name, local owner/manager, unit/local name, public-access status, source identifiers, and reported GIS acres.

### Source-geometry hygiene

The 2026-09-01 refresh encountered normal real-world GIS imperfections in PAD-US:

- **2 non-spatial records** had null geometry and were skipped because they cannot contribute to a map layer.
- **232 spatial records** contained invalid polygon topology and were repaired with GEOS `make_valid()` before Idaho clipping.

Attributes are preserved. Geometry repair is limited to making the published polygons topologically valid enough for spatial clipping; it is not a manual redraw or reinterpretation of the source.

## Ranger Districts

The Ranger District layer complements the broader Administrative Forest polygons by identifying the more specific Forest Service administrative unit responsible for a location. This can support later access, trail, closure, and management-context features without hard-coding district names in consuming apps.

## Source-of-truth rules

- The Census state boundary is the exact clipping boundary for Idaho-specific polygon layers.
- Source-rich/source-faithful files preserve authoritative attributes and geometry after Idaho clipping and necessary topology repair.
- Files ending in `_map.geojson` are simplified with topology preservation for browser delivery; use the richer file for analysis or future derivation.
- Public-land management, USFS Forest boundaries, Ranger Districts, and Wilderness remain separate layers because they answer different questions and can overlap.
- App styling, labels, opacity, line weights, and layer priority belong in the consuming app rather than this repository.

## Refresh

- `scripts/pull_idaho_foundation.py` + `.github/workflows/refresh-foundation.yml` rebuild the Census boundary, USFS Administrative Forests, Wilderness, and USDA mature/old-growth foundation context.
- `scripts/pull_idaho_base_v1_completion.py` (through its resilient runner) + `.github/workflows/refresh-base-v1.yml` rebuild PAD-US public-land managers and USFS Ranger Districts, along with the rich recreation-site layer in `data/access/`.

Upstream queries use an Idaho spatial prefilter where practical, then final geometry is clipped locally against the versioned Census Idaho polygon. Invalid source topology and null geometry are handled explicitly rather than silently dropping or inventing spatial data.
