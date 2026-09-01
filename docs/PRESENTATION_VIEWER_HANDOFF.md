# My Map — Idaho · Presentation Viewer Handoff

Status: **approved direction**

Goal: turn `my-map-idaho` into a beautiful, fast, full-screen map experience without turning the data repository into an application or using Lovable as the source of technical truth.

## Architecture

### 1. `my-map-idaho` — geographic intelligence

Source of truth for versioned Idaho geographic data.

Consumer entry point:

`https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/catalog/base-v1.json`

The catalog exposes stable logical layer IDs and preferred browser delivery paths. App styling remains outside this repository.

### 2. Mapbox Studio — cartography

Owns the visual base map:

- terrain / hillshade;
- contours;
- water styling;
- road hierarchy;
- typography / place labels;
- landcover tone;
- overall mountain-map art direction.

The existing Ride Here custom Mapbox style is useful reference material, but the new viewer should use a published Mapbox Studio style URL so cartographic iteration does not require application-code edits.

### 3. Viewer GitHub repository — technical application shell

A fresh repository connected to the new Lovable project should own:

- Mapbox GL JS initialization;
- catalog loading;
- logical layer registry;
- manifest/shard loading where still required;
- feature selection;
- search / geolocation logic;
- performance and lazy-loading rules;
- environment configuration;
- tests / linting;
- deployment configuration.

GitHub remains the durable source of truth after the initial Lovable visual build.

### 4. Lovable — presentation and interaction design

Use Lovable where it is strongest:

- full-screen responsive shell;
- layer drawer / controls;
- search treatment;
- detail cards / bottom sheets;
- mobile navigation;
- motion and transitions;
- spacing, typography and branded polish.

Avoid spending Lovable credits on routine data wiring, loader refactors, source URLs, or deterministic Mapbox code that can be changed directly in GitHub.

## Initial viewer contract

Recommended environment variables:

```text
VITE_MAPBOX_TOKEN=
VITE_MAPBOX_STYLE_URL=
VITE_MAP_IDAHO_CATALOG_URL=https://raw.githubusercontent.com/enduranceculture/my-map-idaho/main/data/catalog/base-v1.json
```

`VITE_` values are browser-visible. Use only a browser-safe Mapbox public token; never place secret provider or GitHub credentials in frontend environment variables.

## V0 screen

Keep the first presentation version intentionally small:

- one full-viewport Mapbox map;
- minimal brand mark / title;
- layer control;
- search;
- locate-me control;
- click/tap a feature -> one clean detail card or mobile bottom sheet;
- no dashboard homepage;
- no duplicate editorial panels sitting beside the map.

The map is the product.

## Layer behavior

Do not load every Base v1 dataset immediately just because it exists.

Start with a quiet base and progressively expose intelligence:

- state / public-land context at broad scales;
- forests / wilderness / ranger districts as contextual overlays;
- access roads and recreation as the user moves into riding/exploration scales;
- regional USFS trail packs only where coverage exists;
- named water and landforms progressively with zoom;
- old-growth / rockhounding research as deliberate specialty overlays.

Exact visibility, zoom thresholds, colors and ordering belong in the viewer and Mapbox style, not the catalog.

## Performance guardrail

The current `named-flowlines` browser delivery is a four-shard GeoJSON manifest representing 115,879 features. Do **not** treat that as an ideal first-load web payload.

Preferred progression:

1. build the V0 viewer around lighter direct GeoJSON layers;
2. test actual browser/mobile performance;
3. move named flowlines to vector-tile delivery before making them a continuously rendered statewide layer;
4. consider the 9,510-road layer for vector tiles if its simplified GeoJSON becomes a measurable bottleneck.

Keep the source GeoJSON in `my-map-idaho` regardless of presentation delivery format.

## First implementation sequence

1. Create fresh Lovable project and let it establish a fresh GitHub app repository.
2. Confirm repository name and Mapbox public-token / style environment-variable slots.
3. Add the minimal Mapbox + catalog technical foundation through GitHub.
4. Establish one polished Mapbox Studio visual direction.
5. Use Lovable for the responsive visual shell and controls.
6. Return to GitHub for data-layer wiring, performance work and iterative fixes.
7. Test desktop + iPhone before adding more product surface area.

## User involvement

For V0, the user should mainly need to:

- create/connect the fresh Lovable project;
- provide access to the existing Mapbox account through normal project configuration (never paste secret credentials into repository files);
- choose among a small number of cartographic directions;
- approve visual / interaction milestones;
- test the finished experience on desktop and phone.
