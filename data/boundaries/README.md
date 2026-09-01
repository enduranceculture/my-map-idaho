# Idaho boundary / land-management context

Authoritative Idaho context layers used by map consumers for state extent, National Forest context, and Wilderness context.

## Live files

| File | Current features | Source | Use |
| --- | ---: | --- | --- |
| `idaho_census_2025.geojson` | 1 | US Census Bureau 2025 Cartographic Boundary Files, States, 1:500,000 | Exact Idaho state clipping / outline |
| `usfs_administrative_forests_idaho.geojson` | 17 | USFS EDW Administrative Forest Boundaries | Source-faithful Idaho-clipped National Forest geometry |
| `usfs_administrative_forests_idaho_map.geojson` | 17 | Derived from the source-faithful file | Lighter browser/map rendering |
| `usfs_wilderness_idaho.geojson` | 9 | USFS EDW National Wilderness Areas | Source-faithful Idaho-clipped Wilderness geometry |
| `usfs_wilderness_idaho_map.geojson` | 9 | Derived from the source-faithful file | Lighter browser/map rendering |

Feature counts are for the 2026-09-01 foundation snapshot and can change when authoritative upstream data changes.

## Source-of-truth rules

- The Census state boundary is the clipping boundary for Idaho-specific polygon layers.
- Raw/source-faithful files preserve the authoritative polygon geometry after exact clipping to Idaho.
- Files ending in `_map.geojson` are simplified with topology preservation for browser rendering; use the source-faithful file for analysis or future derivation.
- App styling, labels, opacity, line weights, and layer priority belong in the consuming app rather than this repository.

## Refresh

`scripts/pull_idaho_foundation.py` rebuilds these layers from the authoritative sources. `.github/workflows/refresh-foundation.yml` runs the foundation refresh monthly and can also be started manually from GitHub Actions.

The puller uses a small Idaho bounding-box prefilter where upstream ArcGIS services support it, then performs the final clip locally against the Census Idaho polygon. If a prefilter fails, it can fall back to ordinary source pagination rather than accepting incomplete geometry.
