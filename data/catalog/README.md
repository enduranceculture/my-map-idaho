# Consumer catalog

`base-v1.json` is the small, machine-readable entry point for apps that consume **My Map — Idaho**.

It exists so a viewer does not need to scatter hard-coded GitHub filenames throughout its codebase. Each logical layer has a stable `id`, metadata about its scope/geometry/source class, and a preferred browser delivery path.

## Contract

- `raw_base` is prepended to relative delivery paths when loading data from the public repository.
- `delivery.browser.type = "geojson"` means the browser-facing layer can be loaded directly as GeoJSON.
- `delivery.browser.type = "manifest"` means the referenced manifest lists every shard required to reconstruct the logical layer. Load every shard as the same logical layer; shard boundaries have no geographic meaning.
- `delivery.source` points to a more source-faithful representation when one is useful and different from the browser representation.
- `source_class` distinguishes authoritative/institutional data from user-researched map intelligence.

## What does not belong here

The catalog intentionally does **not** define:

- colors or line weights;
- default visibility;
- zoom thresholds;
- Mapbox layer ordering;
- icons;
- popover/card design;
- application navigation.

Those are presentation decisions owned by the consuming app / Mapbox style.

## Performance direction

The catalog is a delivery contract, not a promise that GeoJSON is the permanent delivery format. Large statewide layers can later move to vector tiles while keeping the same logical layer IDs. The first obvious tile candidates are:

1. `named-flowlines`;
2. `drive-access-roads` if direct GeoJSON becomes too heavy for the final viewer.

That lets the presentation layer become faster without changing the source-of-truth organization in this repository.

## Recommended app environment contract

A presentation viewer should keep provider/configuration values in environment variables and never commit secret credentials. A sensible initial contract is:

- `VITE_MAPBOX_TOKEN` — browser-safe Mapbox public token;
- `VITE_MAPBOX_STYLE_URL` — published Mapbox Studio style URL;
- `VITE_MAP_IDAHO_CATALOG_URL` — raw URL to `data/catalog/base-v1.json`.

Vite-prefixed values are browser-visible. Never place a secret GitHub token or secret Mapbox token in them.
